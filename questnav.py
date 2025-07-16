import tkinter as tk
from tkinter import messagebox
import ntcore
import os
import time

# Attempt to import Pillow for image manipulation.
# This is required for the color filter feature.
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
except ImportError:
    print("Pillow library not found. Please install it: pip install Pillow")
    print("The color filter feature will be disabled.")
    Image = None
    ImageTk = None

# --- Configuration ---
# MODIFIED: Changed default IP to local for testing with OutlineViewer
NT_SERVER_IP = "127.0.0.1" 
NT_TABLE_NAME = "SmartDashboard/QuestNavManager"
UPDATE_PERIOD_MS = 1000  # How often to check for connection status

# --- AprilTag Data ---
# Dictionary mapping tag ID to its (x, y) coordinates on the canvas.
APRILTAG_COORDS = {
    1: (750, 333), 2: (750, 100), 3: (550, 88),  4: (500, 130),
    5: (500, 300), 6: (640, 260), 7: (667, 220), 8: (650, 170),
    9: (580, 170), 10: (555, 220), 11: (580, 265),12: (160, 333),
    13: (160, 100), 14: (400, 140), 15: (400, 300), 16: (350, 350),
    17: (260, 260), 18: (240, 220), 19: (260, 165), 20: (320, 165),
    21: (340, 218), 22: (320, 260)
}

class QuestNavManagerDashboard:
    def __init__(self, master):
        self.master = master
        master.title("QuestNav Manager")
        master.geometry("820x520+560+0") # Adjusted size for the larger field
        master.configure(bg="#1a1a2e")

        # --- Data Storage ---
        self.field_bg_photo = None # Must keep a reference to avoid garbage collection
        # self.tag_data stores all info about each tag, including original and filtered images
        # Format: { tag_id: {'canvas_id': id, 'original_photo': PhotoImage, 'filtered_photos': { 'red': PhotoImage, ... } } }
        self.tag_data = {}

        # MODIFIED: Flag to track if we've synced values from NT on connection
        self.initial_sync_done = False

        # --- UI Setup ---
        self._setup_ui()

        # --- NetworkTables Setup ---
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(NT_TABLE_NAME)
        self.inst.startClient4("dashboard")
        self.inst.setServer(NT_SERVER_IP)

        # --- Initial Drawing and Periodic Updates ---
        self._draw_field_and_tags()
        self.periodic_update()

    def _setup_ui(self):
        """Creates and packs all the UI widgets."""
        # Top frame for controls
        control_frame = tk.Frame(self.master, bg="#2a2a3e", padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Field Select
        tk.Label(control_frame, text="Field Select:", fg="white", bg=control_frame['bg']).pack(side=tk.LEFT, padx=(10, 5))
        self.field_var = tk.StringVar(value="-1")
        tk.Entry(control_frame, textvariable=self.field_var, width=5).pack(side=tk.LEFT)

        # Layout Select
        tk.Label(control_frame, text="Layout Select:", fg="white", bg=control_frame['bg']).pack(side=tk.LEFT, padx=(20, 5))
        self.layout_var = tk.StringVar(value="-1")
        tk.Entry(control_frame, textvariable=self.layout_var, width=5).pack(side=tk.LEFT)

        # Apply Button
        apply_button = tk.Button(control_frame, text="Apply", command=self.on_apply_clicked, bg="#39FF14", fg="black", relief=tk.FLAT)
        apply_button.pack(side=tk.LEFT, padx=20)

        # Canvas for the field
        self.canvas = tk.Canvas(self.master, width=800, height=450, bg="black", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, pady=5)
        
        # Status Label
        self.status_label = tk.Label(self.master, text="Connecting...", bd=1, relief=tk.SUNKEN, anchor=tk.W, fg="white", bg="#333")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _draw_field_and_tags(self):
        """Loads and displays the background field and all AprilTag images."""
        # 1. Draw Background
        try:
            self.field_bg_photo = ImageTk.PhotoImage(file="field.png")
            self.canvas.create_image(0, 0, image=self.field_bg_photo, anchor=tk.NW)
        except Exception as e:
            self.canvas.create_text(400, 225, text=f"Error loading field.png:\n{e}", fill="red", font=("Arial", 14))
            print(f"Error: Could not load 'field.png'. {e}")

        # 2. Draw AprilTags
        for tag_id, coords in APRILTAG_COORDS.items():
            try:
                img_path = f"apriltags/{tag_id}.png"
                # Generate a placeholder if the image doesn't exist
                if not os.path.exists(img_path):
                    self._generate_placeholder_tag_image(tag_id)

                # Store original PhotoImage to prevent garbage collection and for resetting visuals
                original_photo = ImageTk.PhotoImage(file=img_path)
                
                canvas_id = self.canvas.create_image(coords[0], coords[1], image=original_photo, tags=f"tag_{tag_id}")
                
                self.tag_data[tag_id] = {
                    'canvas_id': canvas_id,
                    'original_photo': original_photo,
                    'filtered_photos': {} # Cache for filtered images
                }

            except Exception as e:
                print(f"Error loading or placing tag {tag_id}: {e}")

    def on_apply_clicked(self):
        """Handles the 'Apply' button click, sending data to NetworkTables."""
        if not self.inst.isConnected():
            messagebox.showwarning("Not Connected", "Cannot apply changes. Not connected to NetworkTables server.")
            return

        try:
            field_index = int(self.field_var.get())
            layout_index = int(self.layout_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Field and Layout must be integer numbers.")
            return

        print(f"Applying Field: {field_index}, Layout: {layout_index}")

        # Publish values to NetworkTables
        self.table.getIntegerTopic("SelectedFieldIndex").publish().set(field_index)
        self.table.getIntegerTopic("SelectedLayoutIndex").publish().set(layout_index)
        self.table.getBooleanTopic("Changed").publish().set(True)
        
    def periodic_update(self):
        """Periodically checks NT connection and syncs data on first connect."""
        if self.inst.isConnected():
            self.status_label.config(text=f"Connected to {NT_SERVER_IP}", fg="#39FF14")
            
            # MODIFIED: Sync values from NT on the first successful connection
            if not self.initial_sync_done:
                self.sync_inputs_from_nt()
                self.initial_sync_done = True
        else:
            self.status_label.config(text=f"Disconnected - trying to connect to {NT_SERVER_IP}", fg="#FF4136")
            # MODIFIED: Reset the flag on disconnect to allow re-syncing on reconnect
            self.initial_sync_done = False

        # --- FUTURE FEATURE HOOK ---
        # This is where you would read NT keys to control the tag filters.
        self.master.after(UPDATE_PERIOD_MS, self.periodic_update)

    def sync_inputs_from_nt(self):
        """Reads index values from NetworkTables and updates the UI entry boxes."""
        print("Syncing UI with NetworkTables values...")
        
        while self.table.getNumber("SelectedFieldIndex", None) is None or self.table.getNumber("SelectedLayoutIndex", None) is None:
            print("Waiting for SelectedFieldIndex to be set in NetworkTables...")
            time.sleep(0.1)
        # Get the current value from NT. If the key doesn't exist, default to -1.
        field_index = int(self.table.getNumber("SelectedFieldIndex",-1))
        layout_index = int(self.table.getNumber("SelectedLayoutIndex",-1))
        
        # Update the UI variables. This will change the text in the Entry widgets.
        self.field_var.set(str(field_index))
        self.layout_var.set(str(layout_index))
        
        print(self.table.getKeys())
        
        print(f"Synced. Field: {field_index}, Layout: {layout_index}")


    # --- Methods for Future Filter Feature ---

    def _apply_filter_to_image(self, img_path, filter_color):
        """
        Applies a color filter to an image file.
        filter_color should be one of 'red', 'green', 'blue', 'magenta'.
        """
        if not Image: return None
        
        with Image.open(img_path).convert("RGBA") as img:
            r, g, b, a = img.split()
            zeros = Image.new('L', img.size, 0)
            
            if filter_color == 'red':
                filtered_img = Image.merge('RGBA', (r, zeros, zeros, a))
            elif filter_color == 'green':
                filtered_img = Image.merge('RGBA', (zeros, g, zeros, a))
            elif filter_color == 'blue':
                filtered_img = Image.merge('RGBA', (zeros, zeros, b, a))
            elif filter_color == 'magenta': # red + blue
                filtered_img = Image.merge('RGBA', (r, zeros, b, a))
            else:
                return None # No valid filter
                
            return ImageTk.PhotoImage(filtered_img)

    def update_tag_visual(self, tag_id, filter_name):
        """
        Updates a tag's visual on the canvas to a filtered version.
        Creates and caches the filtered image if it doesn't exist.
        
        :param tag_id: The ID of the AprilTag to update (e.g., 5).
        :param filter_name: The name of the filter (e.g., 'red', 'green', 'blue', 'magenta').
        """
        if tag_id not in self.tag_data: return
        
        tag_info = self.tag_data[tag_id]
        
        # Check cache first
        if filter_name in tag_info['filtered_photos']:
            photo_to_show = tag_info['filtered_photos'][filter_name]
        else:
            # Create, cache, and then use the new filtered image
            img_path = f"apriltags/{tag_id}.png"
            new_photo = self._apply_filter_to_image(img_path, filter_name)
            if new_photo:
                tag_info['filtered_photos'][filter_name] = new_photo
                photo_to_show = new_photo
            else: # Invalid filter name, do nothing
                return
        
        self.canvas.itemconfig(tag_info['canvas_id'], image=photo_to_show)

    def reset_tag_visual(self, tag_id):
        """Resets a tag's visual on the canvas to its original, unfiltered image."""
        if tag_id in self.tag_data:
            tag_info = self.tag_data[tag_id]
            self.canvas.itemconfig(tag_info['canvas_id'], image=tag_info['original_photo'])

    def _generate_placeholder_tag_image(self, tag_id):
        """Creates a placeholder image if an AprilTag image is missing."""
        if not Image: return

        if not os.path.exists("apriltags"):
            os.makedirs("apriltags")
        
        img_path = f"apriltags/{tag_id}.png"
        print(f"Generating placeholder for {img_path}...")
        
        img = Image.new('RGB', (40, 40), color = 'darkgrey')
        d = ImageDraw.Draw(img)
        try:
            # Use a basic font if available
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
        
        d.text((10,10), str(tag_id), fill='white', font=font)
        img.save(img_path)


if __name__ == "__main__":
    # Generate placeholder for field.png if it's missing
    if not os.path.exists("field.png"):
        if Image:
            print("Generating placeholder field.png...")
            field_img = Image.new('RGB', (800, 450), color='#004d00')
            ImageDraw.Draw(field_img).text((10, 10), "field.png (placeholder)", fill="white")
            field_img.save("field.png")
        else:
            print("Cannot generate placeholder field.png because Pillow is not installed.")

    root = tk.Tk()
    app = QuestNavManagerDashboard(root)
    root.mainloop()