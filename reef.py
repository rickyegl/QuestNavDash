import tkinter as tk
import math

# --- Data object for each dot ---
class DotNode:
    """A data object representing a single interactive dot on the dashboard."""
    def __init__(self, canvas_id, dot_type, side_id, sub_reef_id=None):
        self.canvas_id = canvas_id
        self.type = dot_type
        self.side_id = side_id
        self.sub_reef_id = sub_reef_id
        self.has_algae = False
        self.is_active = False
        self.is_flagged = False

    def __repr__(self):
        state = f"Active={self.is_active}, Flagged={self.is_flagged}"
        if self.type == 'purple':
            return f"<DotNode: Side={self.side_id}, SubReef={self.sub_reef_id}, {state}>"
        else:
            return f"<DotNode: Side={self.side_id}, HasAlgae={self.has_algae}, {state}>"

# --- NEW: Data object for each hexagon side ---
class HexSideNode:
    """A data object representing one side of the central hexagon."""
    def __init__(self, canvas_id, side_id):
        self.canvas_id = canvas_id  # The ID of the line on the canvas
        self.side_id = side_id      # 0 to 5, identifying the side
        self.is_flagged = False     # The state we want to toggle

    def __repr__(self):
        return f"<HexSideNode: Side={self.side_id}, Flagged={self.is_flagged}>"


class HexDataDashboard:
    def __init__(self, master):
        self.master = master
        master.title("Hex-Grid Data Dashboard")
        master.geometry("550x550+0+0")
        master.configure(bg="#1a1a2e")

        self.CENTER_X, self.CENTER_Y = 275, 275
        self.DOT_SIZE = 20
        self.RADII = {"hexagon": 50, "level_1": 90, "level_2": 140, "level_3": 190, "green_level": 240}
        self.COLORS = {"bg": "#1a1a2e", "purple": "#8A2BE2", "purple_hover": "#be7dfd", "white_toggled": "#FFFFFF", "green": "#39FF14", "green_hover": "#98FB98", "green_toggled": "#1a3b1f", "red_flagged": "#FF4136"}
        self.DOT_OFFSET_ANGLE = 12

        # --- Data stores for all interactive elements ---
        self.dot_nodes = {}
        self.hexagon_sides = {} # NEW dictionary for hexagon side objects

        self.canvas = tk.Canvas(master, width=550, height=550, bg=self.COLORS["bg"], highlightthickness=0)
        self.canvas.pack()

        self.draw_dashboard()
        
        # Bind events for dots
        self.canvas.tag_bind("toggle_dot", "<Button-1>", self.handle_left_click)
        self.canvas.tag_bind("toggle_dot", "<Button-3>", self.handle_right_click)
        self.canvas.tag_bind("toggle_dot", "<Enter>", self.on_dot_enter)
        self.canvas.tag_bind("toggle_dot", "<Leave>", self.on_dot_leave)

        # --- NEW: Bind right-click event for hexagon sides ---
        self.canvas.tag_bind("hexagon_side", "<Button-3>", self.toggle_hexagon_side)

    def get_circle_position(self, radius, angle_degrees):
        angle_radians = math.radians(angle_degrees - 90)
        x = self.CENTER_X + radius * math.cos(angle_radians)
        y = self.CENTER_Y + radius * math.sin(angle_radians)
        return x, y

    def draw_dashboard(self):
        self.draw_orbital_dots()
        self.draw_hexagon()

    # --- MODIFIED: Draws 6 individual lines instead of one polygon ---
    def draw_hexagon(self):
        """Draws a "pointy-topped" hexagon as 6 separate, interactive lines."""
        points = []
        # First, calculate all 6 corner points of the hexagon
        for i in range(6):
            points.append(self.get_circle_position(self.RADII["hexagon"], i * 60 - 30))

        # Now, draw a line between each point and the next, creating a data node
        for i in range(6):
            start_point = points[i]
            # The modulo operator (%) ensures the last point connects back to the first
            end_point = points[(i + 1) % 6] 
            
            line_id = self.canvas.create_line(
                start_point, end_point,
                fill=self.COLORS["purple"], 
                width=20, 
                tags="hexagon_side"  # Apply the tag for event binding
            )
            # Create the data object for this side and store it
            self.hexagon_sides[line_id] = HexSideNode(line_id, i)

    # --- NEW: Event handler for right-clicking a hexagon side ---
    def toggle_hexagon_side(self, event):
        """Toggles a hexagon side between purple and red."""
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        
        # Check if the clicked item is actually a hexagon side
        if clicked_id not in self.hexagon_sides:
            return

        side_node = self.hexagon_sides[clicked_id]
        
        # Toggle the data model state
        side_node.is_flagged = not side_node.is_flagged
        
        # Update the UI based on the new state
        new_color = self.COLORS['red_flagged'] if side_node.is_flagged else self.COLORS['purple']
        self.canvas.itemconfig(clicked_id, fill=new_color)
        
        print(f"Toggled: {side_node}")

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

    def handle_right_click(self, event):
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id not in self.dot_nodes:
            return
        node = self.dot_nodes[clicked_id]
        node.is_flagged = not node.is_flagged
        if node.is_flagged:
            node.is_active = False
        self._update_dot_visuals(node)
        print(f"Right-clicked: {node}")

    def handle_left_click(self, event):
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id not in self.dot_nodes:
            return
        node = self.dot_nodes[clicked_id]
        if node.is_flagged:
            node.is_flagged = False
        else:
            node.is_active = not node.is_active
            if node.type == 'green':
                node.has_algae = node.is_active
        self._update_dot_visuals(node)
        print(f"Left-clicked: {node}")

    def _update_dot_visuals(self, node):
        new_color = ""
        if node.is_flagged:
            new_color = self.COLORS['red_flagged']
        elif node.is_active:
            new_color = self.COLORS['white_toggled'] if node.type == 'purple' else self.COLORS['green_toggled']
        else:
            new_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
        self.canvas.itemconfig(node.canvas_id, fill=new_color)

    def on_dot_enter(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        node = self.dot_nodes.get(dot_id)
        if node and not node.is_active and not node.is_flagged:
            hover_color = self.COLORS['purple_hover'] if node.type == 'purple' else self.COLORS['green_hover']
            self.canvas.itemconfig(dot_id, fill=hover_color)

    def on_dot_leave(self, event):
        dot_id = self.canvas.find_closest(event.x, event.y)[0]
        node = self.dot_nodes.get(dot_id)
        if node and not node.is_active and not node.is_flagged:
            default_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
            self.canvas.itemconfig(dot_id, fill=default_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = HexDataDashboard(root)
    root.mainloop()