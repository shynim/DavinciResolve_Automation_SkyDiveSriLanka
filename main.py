import DaVinciResolveScript as dvr
import os
import re
from datetime import datetime
from tkinter import messagebox

DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"
FOLDER_DATE_PATTERN = r"\s*\d{1,2}/\d{1,2}/\d{4}.*$"
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mxf', '.avi')  # Supported video formats
LOAD_NUMBER_PATTERN = r"L(\d+)$"  # Pattern to extract load number from bin name

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
        self.gui = None
        self.resolve, self.project, self.media_pool = get_resolve_objects()
    
    def create_media_bins(self):
        """Main function to create media bins"""
        try:
            root_folder = self.gui.folder_entry.get()
        
            if not root_folder:
                messagebox.showerror("Error", "Please select a folder first")
                return []

            if not os.path.isdir(root_folder):
                messagebox.showerror("Error", f"Folder not found: {root_folder}")
                return []

            if not self.media_pool:
                messagebox.showwarning("Warning", "Not connected to DaVinci Resolve")
                return []

            root_folder_name = os.path.basename(root_folder)
            date_match = re.search(DATE_PATTERN, root_folder_name)
            date_prefix = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

            root_bin = self.media_pool.GetRootFolder()
            if not root_bin:
                messagebox.showerror("Error", "Could not get root bin from Media Pool")
                return []

            # Find and sort all load videos in the root folder by their numerical value
            load_videos = self._find_and_sort_load_videos(root_folder)
            self.gui.add_log_message(f"Found {len(load_videos)} load videos in root folder\n")
            if load_videos:
                self.gui.add_log_message("Load videos in order:\n" + 
                                       "\n".join(f"{i+1}: {os.path.basename(v)}" 
                                                for i, v in enumerate(load_videos)) + "\n")

            # Process subfolders
            subfolders = [f for f in os.scandir(root_folder) if f.is_dir()]
            if not subfolders:
                messagebox.showinfo("Info", "No subfolders found in selected directory")
                return []

            created_bins = []
            updated_bins = []
            
            for folder in subfolders:
                folder_name = self.clean_folder_name(folder.name)
                bin_name = f"{date_prefix} - {folder_name}"
                load_number = self._get_load_number_from_bin(bin_name)
                
                if not load_number:
                    self.gui.add_log_message(f"Skipping folder {folder_name} - no load number found\n")
                    continue
                
                # Check if bin exists
                bin_folder = self.find_bin_by_name(root_bin, bin_name)
                
                if bin_folder:
                    self.gui.add_log_message(f"Bin already exists: {bin_name} (L{load_number})\n")
                    if self._import_vids(bin_folder, folder.path):
                        updated_bins.append(bin_name)
                    # Import load video to existing bin
                    self._import_load_video(bin_folder, load_number, load_videos)
                else:
                    try:
                        if new_bin := self.media_pool.AddSubFolder(root_bin, bin_name):
                            created_bins.append(bin_name)
                            self.gui.add_log_message(f"Created new bin: {bin_name} (L{load_number})\n")
                            self._import_vids(new_bin, folder.path)
                            # Import load video to new bin
                            self._import_load_video(new_bin, load_number, load_videos)
                        else:
                            self.gui.add_log_message(f"Failed to create: {bin_name}\n")
                    except Exception as e:
                        self.gui.add_log_message(f"Error creating {bin_name}: {str(e)}\n")
                
                self.gui.add_log_message("\n")

            # Summary report
            summary = [
                "\n=== Summary ===",
                f"Total folders scanned: {len(subfolders)}",
                f"New bins created: {len(created_bins)}",
                f"Existing bins updated: {len(updated_bins)}",
                f"Missing files imported: {len(created_bins) + len(updated_bins)}\n\n"
            ]
            self.gui.add_log_message("\n".join(summary))
            
            if created_bins:
                self.gui.add_log_message("\nCreated bins:\n- " + "\n- ".join(created_bins) + "\n")
            if updated_bins:
                self.gui.add_log_message("\nUpdated bins:\n- " + "\n- ".join(updated_bins) + "\n")
            
            return created_bins + updated_bins

        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            return []
    
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
    
    def _find_and_sort_load_videos(self, root_folder):
        """Find all load videos in the root folder and sort them by their numerical value"""
        load_videos = []
        for entry in os.scandir(root_folder):
            if entry.is_file() and entry.name.lower().endswith(VIDEO_EXTENSIONS):
                # Extract all numbers from filename and use the largest one
                numbers = [int(num) for num in re.findall(r'\d+', entry.name)]
                if numbers:
                    # Use the largest number found in filename as the key for sorting
                    max_num = max(numbers)
                    load_videos.append((max_num, entry.path))
        
        # Sort videos by their numerical value
        load_videos.sort(key=lambda x: x[0])
        return [video[1] for video in load_videos]  # Return just the sorted paths
    
    def _get_load_number_from_bin(self, bin_name):
        """Extract load number from bin name (e.g., 'L1' returns 1)"""
        match = re.search(LOAD_NUMBER_PATTERN, bin_name)
        return int(match.group(1)) if match else None
    
    def _import_load_video(self, bin_folder, load_number, load_videos):
        """Import the appropriate load video to the bin based on sorted order"""
        if not load_videos:
            self.gui.add_log_message("No load videos found to import\n")
            return False
        
        # Check if we have enough load videos
        if load_number > len(load_videos):
            self.gui.add_log_message(f"Not enough load videos for L{load_number} (only {len(load_videos)} available)\n")
            return False
        
        # Get the corresponding load video (L1 = first in sorted list, etc.)
        video_path = load_videos[load_number - 1]
        video_name = os.path.basename(video_path)
        
        # Check if load video already exists in bin
        existing_clips = {clip.GetName() for clip in bin_folder.GetClipList()}
        if video_name in existing_clips:
            self.gui.add_log_message(f"Load video already exists in bin: {video_name}\n")
            return True
        
        # Import the video
        result = self.media_pool.ImportMedia([video_path])
        
        if not result:
            self.gui.add_log_message(f"Failed to import load video: {video_name}\n")
            return False
        
        # Move imported clip to the target bin
        root_clip = self.media_pool.GetRootFolder()
        for item in root_clip.GetClipList():
            if item.GetName() == video_name:
                self.media_pool.MoveClips([item], bin_folder)
                self.gui.add_log_message(f"Imported load video {video_name} to L{load_number} bin\n")
                return True
        
        #self.gui.add_log_message(f"Failed to move imported load video to bin\n")
        return False
    
    def _import_vids(self, bin_folder, folder_path):
        """Import videos to bin with logging"""
        missing_files = self.get_missing_files(bin_folder, folder_path)
        
        if not missing_files:
            self.gui.add_log_message(f"No missing files in: {bin_folder.GetName()}\n")
            return False
        
        video_files = [os.path.join(folder_path, f) for f in missing_files]
        result = self.media_pool.ImportMedia(video_files)
        
        if not result:
            self.gui.add_log_message(f"Failed to import missing files to: {bin_folder.GetName()}\n")
            return False
        
        # Move imported items to the target bin
        root_clip = self.media_pool.GetRootFolder()
        for item in root_clip.GetClipList():
            if item.GetName() in missing_files:
                self.media_pool.MoveClips([item], bin_folder)
        
        self.gui.add_log_message(f"Imported {len(missing_files)} files to: {bin_folder.GetName()}\n")
        return True