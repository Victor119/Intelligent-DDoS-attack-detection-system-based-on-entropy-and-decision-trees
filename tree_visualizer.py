import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import ctypes
import threading
import time
import random

class TreeVisualizer:
    def __init__(self, screen_width=1200, screen_height=700, bg_color=(0.2, 0.2, 0.2, 1.0)):
        """Initialize the TreeVisualizer with window settings."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.bg_color = bg_color
        self.root = None
        # Node size and spacing parameters
        self.node_radius = 25      
        self.level_height = 150    
        self.min_node_distance = 80  # Minimum distance between any two nodes
        self.node_width = 120        # Effective width of a node including text
        self.current_node = None

        # Camera/view control
        self.scroll_x = 0
        self.scroll_y = 0
        self.scroll_speed = 20
        self.zoom = 1.0
        self.zoom_factor = 0.1
        self.max_zoom_out = 0.2
        self.max_zoom_in = 2.0
        self.dragging = False
        self.last_x = 0
        self.last_y = 0

        # Colors
        self.node_color = (1.0, 1.0, 1.0)
        self.text_color = (0.89, 0.33, 0.05)
        self.line_color = (0.0, 0.7, 0.0)
        self.highlight_color = (1.0, 0.0, 0.0)
        self.class_benign_color = (0.0, 0.7, 0.0)
        self.class_attack_color = (0.7, 0.0, 0.0)
        self.path_highlight_color = (1.0, 1.0, 0.0)  # Yellow for path highlighting
        self.path_line_color = (1.0, 0.5, 0.0)      # Orange for path lines

        # Progressive coloring system
        self.node_visit_counts = {}  # Track how many times each node has been visited
        self.node_base_colors = {}   # Store the base color assigned to each node
        self.max_visits = 10         # Maximum visits before reaching darkest color
        
        # Base colors for the three color families (light versions)
        self.color_families = {
            'blue': {
                'light': (1.0, 1.0, 1.0),  # White
                'dark': (0.0, 0.2, 0.8)      # Dark blue
            },
            'yellow': {
                'light': (1.0, 1.0, 1.0),  # White
                'dark': (0.8, 0.6, 0.0)      # Dark yellow/gold
            },
            'purple': {
                'light': (1.0, 1.0, 1.0),  # White
                'dark': (0.5, 0.0, 0.8)      # Dark purple
            }
        }
        
        # Culori pentru frunze (benign si ddos) in versiuni light/dark
        self.leaf_color_families = {
            'benign': {
                'light': (0.9, 1.0, 0.9),  # verde foarte deschis
                'dark':  (0.0, 0.5, 0.0)   # verde inchis
            },
            'ddos': {
                'light': (1.0, 0.9, 0.9),  # rosu foarte deschis
                'dark':  (0.5, 0.0, 0.0)   # rosu inchis
            }
        }

        # Tree metrics and layout
        self.tree_height = 0
        self.node_positions = {}  # Store calculated positions for each node
        self.level_widths = {}    # Store required width for each level

        # Path highlighting - use set to store all highlighted nodes from multiple paths
        self.highlighted_paths = set()  # Set of all nodes that have been highlighted
        self.current_path = []  # Current path being processed
        self.path_lock = threading.Lock()  # Thread safety for path updates

        # Font
        self.font = None
        
        # Auto-redraw mechanism
        self.needs_redraw = False
        self.redraw_timer = None

    def set_tree(self, root_node):
        self.root = root_node
        self.tree_height = self.calculate_tree_height(self.root)
        self.calculate_node_positions()
        self.initialize_node_colors()

    def initialize_node_colors(self):
        """Initialize random base colors for all nodes in the tree."""
        if not self.root:
            return
        
        color_names = list(self.color_families.keys())
        self._assign_random_colors(self.root, color_names)

    def _assign_random_colors(self, node, color_names):
        """Recursively assign random colors to all nodes."""
        node_id = id(node)
        
        # Assign a random color family to this node
        self.node_base_colors[node_id] = random.choice(color_names)
        
        # Initialize visit count
        if node_id not in self.node_visit_counts:
            self.node_visit_counts[node_id] = 0
        
        # Process children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._assign_random_colors(child, color_names)

    def get_node_color(self, node):
        """Get the current color for a node based on its visit count."""
        node_id = id(node)
        
        # Check if this is a leaf node with class information
        name = getattr(node, 'name', '')
        is_class = name.startswith("Class:")
        
        if is_class:
            # This is a leaf node - check if benign or ddos
            is_benign = "benign" in name.lower()
            is_ddos = "ddos" in name.lower()
            
            if is_benign or is_ddos:
                visit_count = self.node_visit_counts.get(node_id, 0)
                progress = min(visit_count / self.max_visits, 1.0)
                
                if is_benign:
                    # Benign: white to dark green
                    light_color = (1.0, 1.0, 1.0)  # White
                    dark_color = (0.0, 0.6, 0.0)   # Dark green
                else:  # is_ddos
                    # DDOS: white to dark red
                    light_color = (1.0, 1.0, 1.0)  # White
                    dark_color = (0.6, 0.0, 0.0)   # Dark red
                
                # Interpolate between light and dark
                interpolated_color = (
                    light_color[0] + (dark_color[0] - light_color[0]) * progress,
                    light_color[1] + (dark_color[1] - light_color[1]) * progress,
                    light_color[2] + (dark_color[2] - light_color[2]) * progress
                )
                
                return interpolated_color
        
        # For non-leaf nodes, use the existing progressive coloring system
        if node_id not in self.node_base_colors:
            return self.node_color  # Default white if not initialized
        
        color_family = self.node_base_colors[node_id]
        visit_count = self.node_visit_counts.get(node_id, 0)
        
        # Calculate interpolation factor (0.0 = light, 1.0 = dark)
        progress = min(visit_count / self.max_visits, 1.0)
        
        # Get light and dark colors for this family
        light_color = self.color_families[color_family]['light']
        dark_color = self.color_families[color_family]['dark']
        
        # Interpolate between light and dark
        interpolated_color = (
            light_color[0] + (dark_color[0] - light_color[0]) * progress,
            light_color[1] + (dark_color[1] - light_color[1]) * progress,
            light_color[2] + (dark_color[2] - light_color[2]) * progress
        )
        
        return interpolated_color

    def increment_node_visit(self, node):
        """Increment the visit count for a node."""
        node_id = id(node)
        if node_id not in self.node_visit_counts:
            self.node_visit_counts[node_id] = 0
        self.node_visit_counts[node_id] += 1

    def highlight_path_for_data(self, data_values, column_names):
        """
        Highlight the path through the tree for given data values.
        data_values: list of values corresponding to column_names
        column_names: list of column names in order
        """
        with self.path_lock:
            # Clear current path but keep accumulated highlighted paths
            self.current_path = []
            if not self.root:
                return
            
            # Convert data to a dictionary for easy lookup
            data_dict = {}
            for i, col_name in enumerate(column_names):
                if i < len(data_values):
                    try:
                        # Try to convert to float for numerical comparisons
                        data_dict[col_name] = float(data_values[i])
                    except (ValueError, TypeError):
                        data_dict[col_name] = data_values[i]
            
            # Traverse the tree and find the path
            current_node = self.root
            self.current_path.append(current_node)
            
            while current_node and hasattr(current_node, 'children') and current_node.children:
                # Parse the node name to get attribute and threshold
                node_name = getattr(current_node, 'name', '')
                
                if "<=" in node_name:
                    # Decision node: extract attribute and threshold
                    parts = node_name.split("<= ", 1)
                    if len(parts) == 2:
                        attribute = parts[0].strip()
                        try:
                            threshold = float(parts[1].strip())
                        except ValueError:
                            threshold = parts[1].strip()
                        
                        # Get the data value for this attribute
                        if attribute in data_dict:
                            data_value = data_dict[attribute]
                            
                            #print(f"DEBUG: Comparing {attribute}: {data_value} with threshold {threshold}")
                            
                            # Decide which child to follow
                            if isinstance(data_value, (int, float)) and isinstance(threshold, (int, float)):
                                if data_value <= threshold:
                                    # Go left (first child)
                                    #print(f"DEBUG: {data_value} <= {threshold}, going LEFT")
                                    current_node = current_node.children[0] if current_node.children else None
                                else:
                                    # Go right (second child)
                                    #print(f"DEBUG: {data_value} > {threshold}, going RIGHT")
                                    current_node = current_node.children[1] if len(current_node.children) > 1 else None
                            else:
                                # String comparison
                                if str(data_value) == str(threshold):
                                    #print(f"DEBUG: String match '{data_value}' == '{threshold}', going LEFT")
                                    current_node = current_node.children[0] if current_node.children else None
                                else:
                                    #print(f"DEBUG: String no match '{data_value}' != '{threshold}', going RIGHT")
                                    current_node = current_node.children[1] if len(current_node.children) > 1 else None
                        else:
                            # Attribute not found in data, stop traversal
                            #print(f"DEBUG: Attribute '{attribute}' not found in data")
                            break
                    else:
                        # Can't parse the node, stop
                        #print(f"DEBUG: Cannot parse node '{node_name}'")
                        break
                else:
                    # Leaf node or unparseable node
                    #print(f"DEBUG: Reached leaf or unparseable node: '{node_name}'")
                    break
                
                if current_node:
                    self.current_path.append(current_node)
                    #print(f"DEBUG: Added node to path: '{getattr(current_node, 'name', 'Unknown')}'")
                else:
                    #print(f"DEBUG: Current node is None, stopping traversal")
                    break
            
            # Increment visit count for all nodes in the path and add to highlighted paths
            for node in self.current_path:
                self.increment_node_visit(node)
                self.highlighted_paths.add(node)
                
            #print(f"DEBUG: Final path length: {len(self.current_path)}")
            #print(f"DEBUG: Total highlighted nodes: {len(self.highlighted_paths)}")
        
        # Schedule a redraw
        self.schedule_redraw()

    def schedule_redraw(self):
        """Schedule a redraw to happen in the OpenGL thread."""
        self.needs_redraw = True

    def check_redraw(self):
        """Check if a redraw is needed and trigger it. Called from display function."""
        if self.needs_redraw:
            self.needs_redraw = False
            glutPostRedisplay()

    def init_gl(self):
        glClearColor(*self.bg_color)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.screen_width, 0, self.screen_height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        try:
            self.font = GLUT_BITMAP_8_BY_13
        except:
            try:
                from OpenGL.GLUT.fonts import GLUT_BITMAP_8_BY_13
                self.font = GLUT_BITMAP_8_BY_13
            except:
                try:
                    self.font = glutBitmapHelvetica12
                except:
                    self.font = 7

    def count_leaves(self, node):
        """Count the number of leaf nodes in a subtree."""
        if not hasattr(node, 'children') or not node.children:
            return 1
        return sum(self.count_leaves(child) for child in node.children)

    def calculate_tree_height(self, node, level=0):
        """Calculate the height of the tree."""
        if not hasattr(node, 'children') or not node.children:
            return level + 1
        return max(self.calculate_tree_height(child, level + 1) for child in node.children)

    def calculate_subtree_width(self, node):
        """Calculate the width needed for a subtree based on leaf count."""
        leaf_count = self.count_leaves(node)
        # Each leaf needs at least min_node_distance space
        return max(leaf_count * self.min_node_distance, self.node_width)

    def calculate_node_positions(self):
        """Calculate positions for all nodes to prevent overlap."""
        if not self.root:
            return
        
        self.node_positions = {}
        
        # First pass: calculate the width needed for each subtree
        subtree_widths = {}
        self._calculate_subtree_widths(self.root, subtree_widths)
        
        # Second pass: assign positions based on calculated widths
        root_width = subtree_widths[id(self.root)]
        start_x = 0  # We'll center this later
        start_y = self.screen_height - 100
        
        self._assign_positions(self.root, start_x, start_y, root_width, subtree_widths)
        
        # Center the entire tree
        if self.node_positions:
            min_x = min(pos[0] for pos in self.node_positions.values())
            max_x = max(pos[0] for pos in self.node_positions.values())
            tree_width = max_x - min_x
            
            # Calculate offset to center the tree
            center_offset = (self.screen_width / 2) - (min_x + tree_width / 2)
            
            # Apply centering offset to all positions
            for node_id in self.node_positions:
                x, y = self.node_positions[node_id]
                self.node_positions[node_id] = (x + center_offset, y)

    def _calculate_subtree_widths(self, node, widths):
        """Recursively calculate the width needed for each subtree."""
        if not hasattr(node, 'children') or not node.children:
            # Leaf node
            widths[id(node)] = self.node_width
            return self.node_width
        
        # Internal node - sum of children widths
        total_width = 0
        for child in node.children:
            child_width = self._calculate_subtree_widths(child, widths)
            total_width += child_width
        
        # Ensure minimum distance between siblings
        if len(node.children) > 1:
            total_width += (len(node.children) - 1) * self.min_node_distance
            
        widths[id(node)] = max(total_width, self.node_width)
        return widths[id(node)]

    def _assign_positions(self, node, x, y, available_width, subtree_widths, level=0):
        """Assign actual positions to nodes."""
        node_id = id(node)
        
        if not hasattr(node, 'children') or not node.children:
            # Leaf node - position at center of available space
            self.node_positions[node_id] = (x + available_width / 2, y)
            return
        
        # Internal node
        children = node.children
        num_children = len(children)
        
        # Position current node at center of available space
        self.node_positions[node_id] = (x + available_width / 2, y)
        
        # Calculate positions for children
        child_y = y - self.level_height
        current_x = x
        
        for i, child in enumerate(children):
            child_width = subtree_widths[id(child)]
            
            # Position child in its allocated space
            self._assign_positions(child, current_x, child_y, child_width, subtree_widths, level + 1)
            
            # Move to next child position
            current_x += child_width
            if i < num_children - 1:  # Add spacing between siblings
                current_x += self.min_node_distance

    def is_node_in_highlighted_path(self, node):
        """Check if a node is in the highlighted path."""
        with self.path_lock:
            return node in self.highlighted_paths

    def draw_node(self, node, x, y, highlighted=False):
        """Draw a tree node at the given position."""
        # Determine if this is a leaf ("Class: …") and if benign or attack
        name = getattr(node, 'name', '')
        
        is_class = name.startswith("Class:")

        # Check if this node is in the highlighted path
        in_path = self.is_node_in_highlighted_path(node)

        # Choose color - removed special handling for class nodes here
        if highlighted:
            glColor3f(*self.highlight_color)
        else:
            # Use progressive coloring for all nodes (including leaves)
            node_color = self.get_node_color(node)
            glColor3f(*node_color)

        # Draw ellipse (wider for text)
        width_factor = 1.8  # Increased width to accommodate text better
        glBegin(GL_POLYGON)
        for i in range(30):
            angle = 2.0 * np.pi * i / 30
            glVertex2f(x + self.node_radius * width_factor * np.cos(angle),
                       y + self.node_radius * np.sin(angle))
        glEnd()

        # Outline - thicker for highlighted path
        if in_path:
            glColor3f(1.0, 0.5, 0.0)  # Orange outline for path
            glLineWidth(3.0)
        else:
            glColor3f(0.8, 0.8, 0.8)
            glLineWidth(1.5)
        
        glBegin(GL_LINE_LOOP)
        for i in range(30):
            angle = 2.0 * np.pi * i / 30
            glVertex2f(x + self.node_radius * width_factor * np.cos(angle),
                       y + self.node_radius * np.sin(angle))
        glEnd()

        # Prepare text lines
        glColor3f(*self.text_color)
        lines = []
        if "<=" in name:
            # Decision node: split at '<='
            parts = name.split("<= ", 1)
            if len(parts) == 2:
                col, val = parts
                lines = [f"{col.strip()} <=", val.strip()]
            else:
                lines = [name]
        elif is_class:
            # Leaf node: split at ':'
            parts = name.split(":", 1)
            if len(parts) == 2:
                cls, val = parts
                lines = [f"{cls}:", val.strip()]
            else:
                lines = [name]
        else:
            lines = [name]

        # Draw each line centered in the ellipse
        line_height = 16
        total_height = len(lines) * line_height
        start_y = y + total_height / 2 - line_height / 2
        
        for idx, line in enumerate(lines):
            y_offset = start_y - idx * line_height
            # Center text horizontally
            text_width = len(line) * 6  # Approximate character width
            x_offset = x - text_width / 2
            self.display_text(line, x_offset, y_offset)

        # Draw visit count as small text below the node
        node_id = id(node)
        visit_count = self.node_visit_counts.get(node_id, 0)
        if visit_count > 0:
            glColor3f(0.8, 0.8, 0.8)  # Light gray for visit count
            count_text = f"({visit_count})"
            count_width = len(count_text) * 4
            self.display_text(count_text, x - count_width / 2, y - self.node_radius - 15)
        
    def draw_line(self, x1, y1, x2, y2, is_path_line=False):
        """Draw a line between two points."""
        if is_path_line:
            glColor3f(*self.path_line_color)
            glLineWidth(4.0)
        else:
            glColor3f(*self.line_color)
            glLineWidth(2.0)
        
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()
        
    def display_text(self, text, x, y):
        """Display text at the given position."""
        glRasterPos2f(x, y)
        
        if self.font is None:
            return
            
        try:
            for char in text:
                glutBitmapCharacter(self.font, ord(char))
        except:
            try:
                for char in text:
                    glutBitmapCharacter(0, ord(char))
            except:
                pass

    def draw_tree(self):
        """Draw the entire tree using pre-calculated positions."""
        if not self.root or not self.node_positions:
            return
        
        # Draw all connections first
        self._draw_connections(self.root)
        
        # Then draw all nodes
        self._draw_nodes(self.root)

    def _is_connection_in_path(self, parent, child):
        """Check if a connection between parent and child is in the highlighted path."""
        with self.path_lock:
            # Check if both parent and child are in highlighted paths
            return parent in self.highlighted_paths and child in self.highlighted_paths

    def _draw_connections(self, node):
        """Draw connections between nodes."""
        if not hasattr(node, 'children') or not node.children:
            return
        
        node_id = id(node)
        if node_id not in self.node_positions:
            return
            
        parent_x, parent_y = self.node_positions[node_id]
        parent_x += self.scroll_x
        parent_y += self.scroll_y
        
        for child in node.children:
            child_id = id(child)
            if child_id in self.node_positions:
                child_x, child_y = self.node_positions[child_id]
                child_x += self.scroll_x
                child_y += self.scroll_y
                
                # Check if this connection is in the highlighted path
                is_path_connection = self._is_connection_in_path(node, child)
                
                # Draw line from parent to child
                self.draw_line(parent_x, parent_y - self.node_radius,
                             child_x, child_y + self.node_radius,
                             is_path_connection)
                
                # Recursively draw child connections
                self._draw_connections(child)

    def _draw_nodes(self, node):
        """Draw all nodes."""
        node_id = id(node)
        if node_id in self.node_positions:
            x, y = self.node_positions[node_id]
            
            # Apply scroll offset
            screen_x = x + self.scroll_x
            screen_y = y + self.scroll_y
            
            # Only draw if visible (with some margin)
            margin = 200
            if (screen_x > -margin and screen_x < self.screen_width + margin and
                screen_y > -margin and screen_y < self.screen_height + margin):
                
                highlighted = (node == self.current_node)
                self.draw_node(node, screen_x, screen_y, highlighted)
        
        # Draw children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._draw_nodes(child)

    def get_tree_bounds(self):
        """Get the bounding box of the tree."""
        if not self.node_positions:
            return 0, 0, 0, 0
            
        positions = list(self.node_positions.values())
        min_x = min(pos[0] for pos in positions) - self.node_radius * 2
        max_x = max(pos[0] for pos in positions) + self.node_radius * 2
        min_y = min(pos[1] for pos in positions) - self.node_radius * 2
        max_y = max(pos[1] for pos in positions) + self.node_radius * 2
        
        return min_x, max_x, min_y, max_y

    def draw_help_text(self):
        """Draw help text for navigation."""
        glColor3f(1.0, 1.0, 1.0)
        help_text = [
            "Navigation Controls:",
            "- Mouse Drag: Pan view",
            "",
            "Node Coloring:",
            "- Blue/Yellow/Purple: Random assignment",
            "- Light to Dark: Visit frequency",
            "- Numbers in (): Visit count"
        ]
        
        x = 10
        y = self.screen_height - 20
        for line in help_text:
            self.display_text(line, x, y)
            y -= 15
        
    def display(self):
        """Main display function."""
        # Check if we need to redraw
        self.check_redraw()
        
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.root:
            # Draw the tree
            self.draw_tree()
            
            # Draw help text
            self.draw_help_text()
            
        glutSwapBuffers()


    def mouse(self, button, state, x, y):
        """Handle mouse input."""
        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                self.dragging = True
                self.last_x = x
                self.last_y = y
            else:
                self.dragging = False
        elif button == 3:  # Mouse wheel up
            self.zoom = min(self.zoom + self.zoom_factor, self.max_zoom_in)
            self.calculate_node_positions()
            glutPostRedisplay()
        elif button == 4:  # Mouse wheel down
            self.zoom = max(self.zoom - self.zoom_factor, self.max_zoom_out)
            self.calculate_node_positions()
            glutPostRedisplay()
        
    def motion(self, x, y):
        """Handle mouse motion."""
        if self.dragging:
            dx = x - self.last_x
            dy = y - self.last_y
            self.scroll_x += dx
            self.scroll_y -= dy  # Invert Y because OpenGL Y is bottom-up
            self.last_x = x
            self.last_y = y
            glutPostRedisplay()

    def idle(self):
        """Idle function to check for pending redraws."""
        if self.needs_redraw:
            self.needs_redraw = False
            glutPostRedisplay()
        
    def run(self, window_title="Tree Visualization"):
        """Start and run the visualization."""
        # Initialize GLUT
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_ALPHA)
        glutInitWindowSize(self.screen_width, self.screen_height)
        
        # Convert window_title to bytes for GLUT
        window_title_bytes = window_title.encode('utf-8')
        glutCreateWindow(window_title_bytes)
        
        # Register callbacks
        glutDisplayFunc(self.display)
        glutMouseFunc(self.mouse)
        glutMotionFunc(self.motion)
        glutIdleFunc(self.idle)  # Add idle function for auto-redraw
        
        # Initialize OpenGL settings
        self.init_gl()
        
        # Enter the main loop
        glutMainLoop()

# Global visualizer instance for external control
_global_visualizer = None

def visualize_binary_tree(root_node, window_title="Tree Visualization"):
    global _global_visualizer
    _global_visualizer = TreeVisualizer(screen_width=1400, screen_height=800)
    _global_visualizer.set_tree(root_node)
    _global_visualizer.run(window_title)

def highlight_path_for_data_line(data_values, column_names):
    """
    External function to highlight path for given data values.
    data_values: list of values from a data line
    column_names: list of column names in order
    """
    global _global_visualizer
    if _global_visualizer:
        _global_visualizer.highlight_path_for_data(data_values, column_names)


# If this file is run directly, demonstrate with a sample tree
if __name__ == "__main__":
    from anytree import Node
    
    # Create a more complex sample tree to test overlap prevention
    root = Node("Fwd Pkts/s <= 17.35")
    
    # Left subtree (more complex)
    l_branch = Node("Flow Pkts/s <= 22.41", parent=root)
    l1 = Node("Tot Bwd Pkts <= 345.70", parent=l_branch)
    l2 = Node("Tot on Fwd Pkts <= 192.50", parent=l_branch)
    
    # Add more children to test spacing
    l1_1 = Node("Packet Length Mean <= 100.5", parent=l1)
    l1_2 = Node("Flow Duration <= 5000", parent=l1)
    l2_1 = Node("Bwd Packet Length Max <= 200", parent=l2)
    l2_2 = Node("Forward IAT Total <= 1000", parent=l2)
    
    # Right subtree
    r_branch = Node("Flow Pkts/s <= 8914.24", parent=root)
    r1 = Node("Tot Fwd Pkts <= 4.70", parent=r_branch)
    r2 = Node("Tot on Fwd Pkts <= 0.30", parent=r_branch)
    
    # Leaf nodes for left subtree
    Node("Class: benign", parent=l1_1)
    Node("Class: attack", parent=l1_2)
    Node("Class: benign", parent=l2_1)
    Node("Class: attack", parent=l2_2)
    
    # Leaf nodes for right subtree
    Node("Class: benign", parent=r1)
    Node("Class: attack", parent=r2)
    
    # Visualize it
    visualize_binary_tree(root, "Improved Decision Tree - No Overlap")