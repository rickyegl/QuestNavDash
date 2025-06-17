import tkinter as tk
import math

# --- Step 1: Define the data object for each dot ---
class DotNode:
    """A data object representing a single interactive dot on the dashboard."""
    def __init__(self, canvas_id, dot_type, side_id, sub_reef_id=None):
        self.canvas_id = canvas_id      # The ID of the shape on the canvas
        self.type = dot_type            # 'purple' or 'green'
        self.side_id = side_id          # 0=Top, 1=Top-Right, ..., 5=Top-Left
        
        # Purple dots represent sub-reefs
        self.sub_reef_id = sub_reef_id  # 0 or 1 for purple dots, None for green
        
        # Green dots represent algae presence
        self.has_algae = False          # Boolean, only relevant for green dots
        
        # Universal state for being 'on' or 'off'
        self.is_active = False
        
        # --- NEW: State for being flagged as red ---
        self.is_flagged = False

    def __repr__(self):
        """A friendly representation for printing the object."""
        state = f"Active={self.is_active}, Flagged={self.is_flagged}"
        if self.type == 'purple':
            return f"<DotNode: Side={self.side_id}, SubReef={self.sub_reef_id}, {state}>"
        else:
            return f"<DotNode: Side={self.side_id}, HasAlgae={self.has_algae}, {state}>"

class HexDataDashboard:
    def __init__(self, master):
        self.master = master
        master.title("Hex-Grid Data Dashboard")
        master.geometry("550x550+0+0")
        master.configure(bg="#1a1a2e")

        # --- Configuration (mostly unchanged) ---
        self.CENTER_X, self.CENTER_Y = 275, 275
        self.DOT_SIZE = 20
        self.RADII = {"hexagon": 50, "level_1": 90, "level_2": 140, "level_3": 190, "green_level": 240}
        # --- NEW: Added red color ---
        self.COLORS = {"bg": "#1a1a2e", "purple": "#8A2BE2", "purple_hover": "#be7dfd", "white_toggled": "#FFFFFF", "green": "#39FF14", "green_hover": "#98FB98", "green_toggled": "#1a3b1f", "red_flagged": "#FF4136"}
        self.DOT_OFFSET_ANGLE = 12

        self.dot_nodes = {}

        self.canvas = tk.Canvas(master, width=550, height=550, bg=self.COLORS["bg"], highlightthickness=0)
        self.canvas.pack()

        self.draw_dashboard()
        # Bind left-click, right-click, and hover events
        self.canvas.tag_bind("toggle_dot", "<Button-1>", self.handle_left_click)
        # --- NEW: Binding for right-click ---
        # Note: On macOS, right-click can sometimes be <Button-2>
        self.canvas.tag_bind("toggle_dot", "<Button-3>", self.handle_right_click)
        self.canvas.tag_bind("toggle_dot", "<Enter>", self.on_dot_enter)
        self.canvas.tag_bind("toggle_dot", "<Leave>", self.on_dot_leave)

    def get_circle_position(self, radius, angle_degrees):
        angle_radians = math.radians(angle_degrees - 90)
        x = self.CENTER_X + radius * math.cos(angle_radians)
        y = self.CENTER_Y + radius * math.sin(angle_radians)
        return x, y

    def draw_dashboard(self):
        self.draw_orbital_dots()
        self.draw_hexagon()

    def draw_hexagon(self):
        points = []
        for i in range(6):
            points.extend(self.get_circle_position(self.RADII["hexagon"], i * 60 - 30))
        self.canvas.create_polygon(points, outline=self.COLORS["purple"], width=3, fill="")

    def draw_orbital_dots(self):
        purple_radii = [self.RADII['level_1'], self.RADII['level_2'], self.RADII['level_3']]
        r = self.DOT_SIZE
        side_center_angles = [0, 60, 120, 180, 240, 300]

        for side_id, center_angle in enumerate(side_center_angles):
            for radius in purple_radii:
                angles = [center_angle - self.DOT_OFFSET_ANGLE, center_angle + self.DOT_OFFSET_ANGLE]
                for sub_reef_id, angle in enumerate(angles):
                    x, y = self.get_circle_position(radius, angle)
                    dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["purple"], outline="", tags="toggle_dot")
                    self.dot_nodes[dot_id] = DotNode(dot_id, 'purple', side_id, sub_reef_id)

            x, y = self.get_circle_position(self.RADII['green_level'], center_angle)
            dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["green"], outline="", tags="toggle_dot")
            self.dot_nodes[dot_id] = DotNode(dot_id, 'green', side_id)

    # --- NEW: Right-click handler ---
    def handle_right_click(self, event):
        """Handles right-clicks to toggle the 'flagged' (red) state."""
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id not in self.dot_nodes:
            return

        node = self.dot_nodes[clicked_id]
        
        # Toggle the flagged state
        node.is_flagged = not node.is_flagged
        
        # A flagged dot cannot also be active. If we flag it, deactivate it.
        if node.is_flagged:
            node.is_active = False

        self._update_dot_visuals(node)
        print(f"Right-clicked: {node}")

    # --- MODIFIED: Renamed and updated left-click handler ---
    def handle_left_click(self, event):
        """Handles left-clicks to toggle 'active' state or to un-flag a red dot."""
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id not in self.dot_nodes:
            return

        node = self.dot_nodes[clicked_id]

        # If it's flagged red, a left click will un-flag it.
        if node.is_flagged:
            node.is_flagged = False
        # Otherwise, toggle its active state as normal.
        else:
            node.is_active = not node.is_active
            if node.type == 'green':
                node.has_algae = node.is_active
        
        self._update_dot_visuals(node)
        print(f"Left-clicked: {node}")

    # --- NEW: Centralized function to update a dot's color based on its state ---
    def _update_dot_visuals(self, node):
        """Sets the dot's color based on its current state properties."""
        new_color = ""
        # Priority 1: Flagged (red)
        if node.is_flagged:
            new_color = self.COLORS['red_flagged']
        # Priority 2: Active (white or dark green)
        elif node.is_active:
            new_color = self.COLORS['white_toggled'] if node.type == 'purple' else self.COLORS['green_toggled']
        # Default: Inactive (purple or bright green)
        else:
            new_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
        
        self.canvas.itemconfig(node.canvas_id, fill=new_color)

    # --- MODIFIED: Hover effects now ignore flagged dots ---
    def on_dot_enter(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        node = self.dot_nodes.get(dot_id)
        # Only show hover effect if the dot is not active AND not flagged
        if node and not node.is_active and not node.is_flagged:
            hover_color = self.COLORS['purple_hover'] if node.type == 'purple' else self.COLORS['green_hover']
            self.canvas.itemconfig(dot_id, fill=hover_color)

    def on_dot_leave(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        node = self.dot_nodes.get(dot_id)
        # Only revert color if the dot is not active AND not flagged
        if node and not node.is_active and not node.is_flagged:
            default_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
            self.canvas.itemconfig(dot_id, fill=default_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = HexDataDashboard(root)
    root.mainloop()