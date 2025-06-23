import DaVinciResolveScript as dvr

import os
import re
from datetime import datetime
from tkinter import messagebox

DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"
FOLDER_DATE_PATTERN = r"\s*\d{1,2}/\d{1,2}/\d{4}.*$"
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mxf', '.avi')  # Supported video formats

def get_resolve_objects():
    """Safely get Resolve objects with error handling"""
    try:
        resolve = dvr.scriptapp("Resolve")
        project = resolve.GetProjectManager().GetCurrentProject()
        return resolve, project, project.GetMediaPool() if project else None
    except (NameError, AttributeError) as e:
        print(f"Error getting Resolve objects: {str(e)}")
        return None, None, None

class BinCreatorApp:
    def __init__(self):
        self.resolve, self.project, self.media_pool = get_resolve_objects()
    
    def create_media_bins(self, folder_path, log_callback):
        """Main function to create media bins"""
        try:
            if not self._validate_inputs(folder_path):
                return []

            root_folder_name = os.path.basename(folder_path)
            date_match = re.search(DATE_PATTERN, root_folder_name)
            date_prefix = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

            root_bin = self.media_pool.GetRootFolder()
            if not root_bin:
                messagebox.showerror("Error", "Could not get root bin from Media Pool")
                return []

            # Process subfolders
            subfolders = [f for f in os.scandir(folder_path) if f.is_dir()]
            if not subfolders:
                messagebox.showinfo("Info", "No subfolders found in selected directory")
                return []

            created_bins = []
            updated_bins = []
            
            for folder in subfolders:
                folder_name = self.clean_folder_name(folder.name)
                bin_name = f"{date_prefix} - {folder_name}"
                
                # Check if bin exists
                bin_folder = self.find_bin_by_name(root_bin, bin_name)
                
                if bin_folder:
                    log_callback(f"Bin already exists: {bin_name}\n")
                    if self._import_vids(bin_folder, folder.path, log_callback):
                        updated_bins.append(bin_name)
                else:
                    try:
                        if new_bin := self.media_pool.AddSubFolder(root_bin, bin_name):
                            created_bins.append(bin_name)
                            log_callback(f"Created new bin: {bin_name}\n")
                            self._import_vids(new_bin, folder.path, log_callback)
                        else:
                            log_callback(f"Failed to create: {bin_name}\n")
                    except Exception as e:
                        log_callback(f"Error creating {bin_name}: {str(e)}\n")
                
                log_callback("\n")

            # Summary report
            summary = [
                "\n=== Summary ===",
                f"Total folders scanned: {len(subfolders)}",
                f"New bins created: {len(created_bins)}",
                f"Existing bins updated: {len(updated_bins)}",
                f"Missing files imported: {len(created_bins) + len(updated_bins)}\n\n"
            ]
            log_callback("\n".join(summary))
            
            if created_bins:
                log_callback("\nCreated bins:\n- " + "\n- ".join(created_bins) + "\n")
            if updated_bins:
                log_callback("\nUpdated bins:\n- " + "\n- ".join(updated_bins) + "\n")
            
            return created_bins + updated_bins

        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            return []
    
    def _validate_inputs(self, folder_path):
        """Validate user inputs"""
        if not folder_path:
            messagebox.showerror("Error", "Please select a folder first")
            return False
        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", f"Folder not found: {folder_path}")
            return False
        if not self.media_pool:
            messagebox.showwarning("Warning", "Not connected to DaVinci Resolve")
            return False
        return True
    
    def clean_folder_name(self, folder_name):
        """Clean folder name by removing trailing dates/times"""
        return re.sub(FOLDER_DATE_PATTERN, "", folder_name).strip()
    
    def find_bin_by_name(self, bin_folder, target_name):
        """Find a bin by name in the folder structure"""
        if bin_folder.GetName() == target_name:
            return bin_folder
        for subfolder in bin_folder.GetSubFolderList():
            found = self.find_bin_by_name(subfolder, target_name)
            if found:
                return found
        return None

    def get_missing_files(self, bin_folder, folder_path):
        """Compare files on disk with clips in bin and return missing files"""
        existing_clips = {clip.GetName() for clip in bin_folder.GetClipList()}
        disk_files = {entry.name for entry in os.scandir(folder_path) 
                    if entry.is_file() and entry.name.lower().endswith(VIDEO_EXTENSIONS)}
        return disk_files - existing_clips
    
    def _import_vids(self, bin_folder, folder_path, log_callback):
        """Import videos to bin with logging"""
        missing_files = self.get_missing_files(bin_folder, folder_path)
        
        if not missing_files:
            log_callback(f"No missing files in: {bin_folder.GetName()}\n")
            return False
        
        video_files = [os.path.join(folder_path, f) for f in missing_files]
        result = self.media_pool.ImportMedia(video_files)
        
        if not result:
            log_callback(f"Failed to import missing files to: {bin_folder.GetName()}\n")
            return False
        
        # Move imported items to the target bin
        root_clip = self.media_pool.GetRootFolder()
        for item in root_clip.GetClipList():
            if item.GetName() in missing_files:
                self.media_pool.MoveClips([item], bin_folder)
        
        log_callback(f"Imported {len(missing_files)} files to: {bin_folder.GetName()}\n")
        return True