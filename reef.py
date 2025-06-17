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

    def __repr__(self):
        """A friendly representation for printing the object."""
        if self.type == 'purple':
            return (f"<DotNode: Side={self.side_id}, SubReef={self.sub_reef_id}, "
                    f"Active={self.is_active}>")
        else:
            return (f"<DotNode: Side={self.side_id}, HasAlgae={self.has_algae}, "
                    f"Active={self.is_active}>")

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
        self.COLORS = {"bg": "#1a1a2e", "purple": "#8A2BE2", "purple_hover": "#be7dfd", "white_toggled": "#FFFFFF", "green": "#39FF14", "green_hover": "#98FB98", "green_toggled": "#1a3b1f"}
        self.DOT_OFFSET_ANGLE = 12

        # --- The new data store: a dictionary of DotNode objects ---
        self.dot_nodes = {}

        self.canvas = tk.Canvas(master, width=550, height=550, bg=self.COLORS["bg"], highlightthickness=0)
        self.canvas.pack()

        self.draw_dashboard()
        self.canvas.tag_bind("toggle_dot", "<Button-1>", self.toggle_dot_state)
        self.canvas.tag_bind("toggle_dot", "<Enter>", self.on_dot_enter)
        self.canvas.tag_bind("toggle_dot", "<Leave>", self.on_dot_leave)

    def get_circle_position(self, radius, angle_degrees):
        angle_radians = math.radians(angle_degrees - 90) # Adjust to make 0 degrees point up
        x = self.CENTER_X + radius * math.cos(angle_radians)
        y = self.CENTER_Y + radius * math.sin(angle_radians)
        return x, y

    def draw_dashboard(self):
        self.draw_orbital_dots()
        self.draw_hexagon()

    def draw_hexagon(self):
        """Draws a "pointy-topped" hexagon."""
        points = []
        for i in range(6):
            # Start at 0 degrees for a pointy-topped hexagon
            points.extend(self.get_circle_position(self.RADII["hexagon"], i * 60-30))
        self.canvas.create_polygon(points, outline=self.COLORS["purple"], width=3, fill="")

    def draw_orbital_dots(self):
        """Draws all dots and creates the corresponding DotNode objects."""
        purple_radii = [self.RADII['level_1'], self.RADII['level_2'], self.RADII['level_3']]
        r = self.DOT_SIZE

        # --- Re-oriented Side Angles ---
        # 0=Top(90), 1=TR(30), 2=BR(-30), 3=Bot(-90), 4=BL(-150), 5=TL(150)
        # We define the center angle of each of the 6 sides
        side_center_angles = [0, 60, 120, 180, 240, 300]

        for side_id, center_angle in enumerate(side_center_angles):
            # Draw Purple Dots and create their nodes
            for radius in purple_radii:
                # Create the two dots for each side
                angles = [center_angle - self.DOT_OFFSET_ANGLE, center_angle + self.DOT_OFFSET_ANGLE]
                for sub_reef_id, angle in enumerate(angles):
                    x, y = self.get_circle_position(radius, angle)
                    dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["purple"], outline="", tags="toggle_dot")
                    # Create the data object and store it
                    self.dot_nodes[dot_id] = DotNode(dot_id, 'purple', side_id, sub_reef_id)

            # Draw Green Dots and create their nodes
            x, y = self.get_circle_position(self.RADII['green_level'], center_angle)
            dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["green"], outline="", tags="toggle_dot")
            # Create the data object for the green dot and store it
            self.dot_nodes[dot_id] = DotNode(dot_id, 'green', side_id)


    def toggle_dot_state(self, event):
        """Toggles the state of the DOT OBJECT and updates the UI to match."""
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        
        if clicked_id not in self.dot_nodes:
            return

        # Get the actual data object for the clicked dot
        node = self.dot_nodes[clicked_id]

        # --- Update the data model first ---
        node.is_active = not node.is_active
        if node.type == 'green':
            node.has_algae = node.is_active

        # --- Then, update the UI based on the new data state ---
        new_color = ""
        if node.is_active:
            new_color = self.COLORS['white_toggled'] if node.type == 'purple' else self.COLORS['green_toggled']
        else:
            new_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
        
        self.canvas.itemconfig(clicked_id, fill=new_color)
        
        # Print the object to prove the data has been updated
        print(f"Toggled: {node}")

    def on_dot_enter(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        if dot_id in self.dot_nodes and not self.dot_nodes[dot_id].is_active:
            dot_type = self.dot_nodes[dot_id].type
            hover_color = self.COLORS['purple_hover'] if dot_type == 'purple' else self.COLORS['green_hover']
            self.canvas.itemconfig(dot_id, fill=hover_color)

    def on_dot_leave(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        if dot_id in self.dot_nodes and not self.dot_nodes[dot_id].is_active:
            dot_type = self.dot_nodes[dot_id].type
            default_color = self.COLORS['purple'] if dot_type == 'purple' else self.COLORS['green']
            self.canvas.itemconfig(dot_id, fill=default_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = HexDataDashboard(root)
    root.mainloop()