import tkinter as tk
import math
import ntcore

# --- Configuration ---
# For local testing with OutlineViewer, use "127.0.0.1"
# For connecting to a RoboRIO, use its IP, e.g., "10.66.47.2" or "roborio-6647-frc.local"
NT_SERVER_IP = "127.0.0.1" 
NT_TABLE_NAME = "SmartDashboard/ReefState"
UPDATE_PERIOD_MS = 100 # How often to check for updates from NetworkTables

# --- Data object for each dot ---
class DotNode:
    """A data object representing a single interactive dot on the dashboard."""
    def __init__(self, canvas_id, dot_type, side_id, sub_reef_id=None, radius_name=None, level_name=None):
        self.canvas_id = canvas_id
        self.type = dot_type
        self.side_id = side_id
        self.sub_reef_id = sub_reef_id # 0 or 1 for purple, None for green
        self.radius_name = radius_name # e.g., 'level_1'
        self.level_name = level_name   # e.g., 'L2' (from Java code)
        self.has_algae = False
        self.is_active = False
        self.is_flagged = False

    def __repr__(self):
        state = f"Active={self.is_active}, Flagged={self.is_flagged}"
        if self.type == 'purple':
            return f"<DotNode: Side={self.side_id}, SubReef={self.sub_reef_id}, Level={self.level_name}, {state}>"
        else:
            return f"<DotNode: Side={self.side_id}, Type=Green, {state}>"

# --- Data object for each hexagon side (now a trapezoid) ---
class HexSideNode:
    """A data object representing one side of the central hexagon."""
    def __init__(self, canvas_id, side_id):
        self.canvas_id = canvas_id
        self.side_id = side_id
        self.is_flagged = False

    def __repr__(self):
        return f"<HexSideNode: Side={self.side_id}, Flagged={self.is_flagged}>"


class HexDataDashboard:
    def __init__(self, master):
        self.master = master
        master.title("Hex-Grid Data Dashboard (Sync Enabled)")
        master.geometry("550x580+0+0")
        master.configure(bg="#1a1a2e")

        self.CENTER_X, self.CENTER_Y = 275, 275
        self.DOT_SIZE = 20
        self.RADII = { "hex_outer": 65, "hex_inner": 45, "level_1": 90, "level_2": 140, "level_3": 190, "green_level": 240 }
        self.COLORS = {"bg": "#1a1a2e", "purple": "#8A2BE2", "purple_hover": "#be7dfd", "white_toggled": "#FFFFFF", "green": "#39FF14", "green_hover": "#98FB98", "green_toggled": "#1a3b1f", "red_flagged": "#FF4136"}
        self.DOT_OFFSET_ANGLE = 12

        # Map Python radius names to Java Level names
        self.level_map = {"level_1": "L2", "level_2": "L3", "level_3": "L4"}
        self.inverse_level_map = {v: k for k, v in self.level_map.items()}

        # Lookups for mapping NT data to GUI elements
        self.dot_nodes = {} # canvas_id -> Node
        self.purple_dots_lookup = {} # (side_id, sub_reef_id, radius_name) -> Node
        self.green_dots_lookup = {}  # side_id -> Node
        self.hexagon_sides = {} # canvas_id -> Node
        self.hex_sides_lookup = {} # side_id -> Node
        
        self.currently_hovered_id = None

        self.canvas = tk.Canvas(master, width=550, height=550, bg=self.COLORS["bg"], highlightthickness=0)
        self.canvas.pack()

        # --- NetworkTables Setup ---
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(NT_TABLE_NAME)
        self.inst.startClient4("dashboard")
        self.inst.setServer(NT_SERVER_IP)
        
        self.status_label = tk.Label(master, text="Connecting...", bd=1, relief=tk.SUNKEN, anchor=tk.W, fg="white", bg="#333")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        # --- End NetworkTables Setup ---

        self.draw_dashboard()
        self.bind_events()
        
        self.periodic_update() # Start the sync loop

    # --- Drawing and Initialization ---
    def draw_dashboard(self):
        self.draw_orbital_dots()
        self.draw_hexagon()

    def bind_events(self):
        self.canvas.tag_bind("toggle_dot", "<Button-1>", self.handle_left_click)
        self.canvas.tag_bind("toggle_dot", "<Button-3>", self.handle_right_click)
        self.canvas.tag_bind("toggle_dot", "<Enter>", self.on_dot_enter)
        self.canvas.tag_bind("toggle_dot", "<Leave>", self.on_dot_leave)
        self.canvas.tag_bind("hexagon_side", "<Button-3>", self.handle_hex_side_toggle)

    def draw_hexagon(self):
        outer_points, inner_points = [], []
        for i in range(6):
            angle = i * 60 - 30
            outer_points.append(self.get_circle_position(self.RADII["hex_outer"], angle))
            inner_points.append(self.get_circle_position(self.RADII["hex_inner"], angle))

        for i in range(6):
            trapezoid_points = [outer_points[i], outer_points[(i + 1) % 6], inner_points[(i + 1) % 6], inner_points[i]]
            poly_id = self.canvas.create_polygon(trapezoid_points, fill=self.COLORS["purple"], outline="", tags="hexagon_side")
            node = HexSideNode(poly_id, i)
            self.hexagon_sides[poly_id] = node
            self.hex_sides_lookup[i] = node

    def draw_orbital_dots(self):
        purple_radii_names = ['level_1', 'level_2', 'level_3']
        r = self.DOT_SIZE
        side_center_angles = [0, 60, 120, 180, 240, 300]

        for side_id, center_angle in enumerate(side_center_angles):
            # Purple Dots (Sub-Reefs)
            for radius_name in purple_radii_names:
                radius = self.RADII[radius_name]
                level_name = self.level_map[radius_name]
                angles = [center_angle + self.DOT_OFFSET_ANGLE, center_angle - self.DOT_OFFSET_ANGLE]
                for sub_reef_id, angle in enumerate(angles):
                    x, y = self.get_circle_position(radius, angle)
                    dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["purple"], outline="", tags="toggle_dot")
                    node = DotNode(dot_id, 'purple', side_id, sub_reef_id, radius_name=radius_name, level_name=level_name)
                    self.dot_nodes[dot_id] = node
                    self.purple_dots_lookup[(side_id, sub_reef_id, radius_name)] = node
            
            # Green Dot (Algae)
            x, y = self.get_circle_position(self.RADII['green_level'], center_angle)
            dot_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.COLORS["green"], outline="", tags="toggle_dot")
            node = DotNode(dot_id, 'green', side_id)
            self.dot_nodes[dot_id] = node
            self.green_dots_lookup[side_id] = node

    # --- Event Handlers (User Interaction) ---
    def handle_hex_side_toggle(self, event):
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id in self.hexagon_sides:
            node = self.hexagon_sides[clicked_id]
            node.is_flagged = not node.is_flagged
            self._update_hex_side_visuals(node)
            self.publish_hex_side_state(node)
            print(f"Toggled and Published: {node}")

    def handle_right_click(self, event):
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id in self.dot_nodes:
            node = self.dot_nodes[clicked_id]
            node.is_flagged = not node.is_flagged
            if node.is_flagged:
                node.is_active = False # Flagging overrides active state
            self._update_dot_visuals(node)
            self.publish_dot_state(node)
            print(f"Right-clicked and Published: {node}")

    def handle_left_click(self, event):
        clicked_id = self.canvas.find_closest(event.x, event.y)[0]
        if clicked_id in self.dot_nodes:
            node = self.dot_nodes[clicked_id]
            if node.is_flagged:
                node.is_flagged = False # Unflag on left-click
            else:
                node.is_active = not node.is_active
            if node.type == 'green':
                node.has_algae = node.is_active
            self._update_dot_visuals(node)
            self.publish_dot_state(node)
            print(f"Left-clicked and Published: {node}")

    # --- NetworkTables Publish Methods (Python -> Java) ---
    def publish_dot_state(self, node):
        if node.is_flagged:
            state_str = "RESTRICTED"
        elif node.is_active:
            state_str = "GAMEPIECE"
        else:
            state_str = "EMPTY"

        if node.type == 'green':
            entry = self.table.getStringTopic(f"Side{node.side_id}/Algae").publish()
            entry.set(state_str)
        elif node.type == 'purple':
            path = f"Side{node.side_id}/{node.sub_reef_id}/{node.level_name}"
            entry = self.table.getStringTopic(path).publish()
            entry.set(state_str)
    
    def publish_hex_side_state(self, node):
        state_str = "RESTRICTED" if node.is_flagged else "ALLOWED"
        entry = self.table.getStringTopic(f"Side{node.side_id}/State").publish()
        entry.set(state_str)

    # --- NetworkTables Sync & Update (Java -> Python) ---
    def periodic_update(self):
        """Main loop called periodically to update connection status and sync data."""
        if self.inst.isConnected():
            self.status_label.config(text=f"Connected to {NT_SERVER_IP}", fg="#39FF14")
            self.sync_from_nt()
        else:
            self.status_label.config(text=f"Disconnected - trying to connect to {NT_SERVER_IP}", fg="#FF4136")
        
        self.master.after(UPDATE_PERIOD_MS, self.periodic_update)

    def sync_from_nt(self):
        """Read all values from NetworkTables and update the GUI if they differ."""
        # Define mappings from NT string values to internal states
        stick_state_map = {"EMPTY": (False, False), "GAMEPIECE": (True, False), "RESTRICTED": (False, True)}
        side_state_map = {"ALLOWED": False, "RESTRICTED": True}

        for side_id in range(6):
            side_table = self.table.getSubTable(f"Side{side_id}")
            
            # Sync Hexagon Side State
            node = self.hex_sides_lookup.get(side_id)
            if node:
                nt_val = side_table.getString("State", "ALLOWED")
                new_flagged = side_state_map.get(nt_val, False)
                if node.is_flagged != new_flagged:
                    node.is_flagged = new_flagged
                    self._update_hex_side_visuals(node)
            
            # Sync Algae (Green) Dot State
            node = self.green_dots_lookup.get(side_id)
            if node:
                nt_val = side_table.getString("Algae", "EMPTY")
                new_active, new_flagged = stick_state_map.get(nt_val, (False, False))
                if node.is_active != new_active or node.is_flagged != new_flagged:
                    node.is_active = new_active
                    node.is_flagged = new_flagged
                    node.has_algae = new_active
                    self._update_dot_visuals(node)

            # Sync Sub-Reef (Purple) Dot States
            for sub_reef_id in range(2):
                branch_table = side_table.getSubTable(str(sub_reef_id))
                for level_name, radius_name in self.inverse_level_map.items():
                    node = self.purple_dots_lookup.get((side_id, sub_reef_id, radius_name))
                    if node:
                        nt_val = branch_table.getString(level_name, "EMPTY")
                        new_active, new_flagged = stick_state_map.get(nt_val, (False, False))
                        if node.is_active != new_active or node.is_flagged != new_flagged:
                            node.is_active = new_active
                            node.is_flagged = new_flagged
                            self._update_dot_visuals(node)

    # --- Visual Update and Utility Methods ---
    def _update_dot_visuals(self, node):
        """Updates a dot's color based on its state, without publishing."""
        new_color = ""
        if node.is_flagged:
            new_color = self.COLORS['red_flagged']
        elif node.is_active:
            new_color = self.COLORS['white_toggled'] if node.type == 'purple' else self.COLORS['green_toggled']
        else: # Not active, not flagged
            # Check if it's currently being hovered over
            if node.canvas_id == self.currently_hovered_id:
                 new_color = self.COLORS['purple_hover'] if node.type == 'purple' else self.COLORS['green_hover']
            else:
                 new_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
        self.canvas.itemconfig(node.canvas_id, fill=new_color)

    def _update_hex_side_visuals(self, node):
        """Updates a hex side's color based on its state, without publishing."""
        new_color = self.COLORS['red_flagged'] if node.is_flagged else self.COLORS['purple']
        self.canvas.itemconfig(node.canvas_id, fill=new_color)

    def on_dot_enter(self, event):
        new_hovered_id = self.canvas.find_closest(event.x, event.y)[0]
        if self.currently_hovered_id and self.currently_hovered_id != new_hovered_id:
            self.reset_hover_visuals(self.currently_hovered_id)
        
        self.currently_hovered_id = new_hovered_id
        node = self.dot_nodes.get(new_hovered_id)
        if node and not node.is_active and not node.is_flagged:
            hover_color = self.COLORS['purple_hover'] if node.type == 'purple' else self.COLORS['green_hover']
            self.canvas.itemconfig(new_hovered_id, fill=hover_color)

    def on_dot_leave(self, event):
        if self.currently_hovered_id:
            self.reset_hover_visuals(self.currently_hovered_id)
            self.currently_hovered_id = None
            
    def reset_hover_visuals(self, canvas_id):
        node = self.dot_nodes.get(canvas_id)
        # Only reset color if it's in a non-toggled, non-flagged state
        if node and not node.is_active and not node.is_flagged:
            default_color = self.COLORS['purple'] if node.type == 'purple' else self.COLORS['green']
            self.canvas.itemconfig(canvas_id, fill=default_color)

    def get_circle_position(self, radius, angle_degrees):
        angle_radians = math.radians(angle_degrees - 90)
        x = self.CENTER_X + radius * math.cos(angle_radians)
        y = self.CENTER_Y + radius * math.sin(angle_radians)
        return x, y

if __name__ == "__main__":
    root = tk.Tk()
    app = HexDataDashboard(root)
    root.mainloop()