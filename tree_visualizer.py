import sys
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import threading
import random
import time

class TreeVisualizer:
    
    def __init__(self, screen_width=1200, screen_height=700, bg_color=(0.2, 0.2, 0.2, 1.0)):
        """Initialize the TreeVisualizer""" 
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.bg_color = bg_color
        self.root = None
        
        # Node size and spacing parameters
        self.node_radius = 18          
        self.level_height = 60         
        self.min_node_distance = 4     
        self.node_width = 90           
        self.current_node = None

        # Camera/view control cu zoom extins
        self.scroll_x = 0
        self.scroll_y = 0
        self.scroll_speed = 20
        self.zoom = 1.0
        self.zoom_factor = 0.1
        self.max_zoom_out = 0.01
        self.max_zoom_in = 3.0
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        
        # Text visibility thresholds ajustate pentru zoom extins
        self.text_visible_threshold = 0.3
        self.text_invisible_threshold = 0.03

        # Colors (rest remains the same...)
        self.node_color = (1.0, 1.0, 1.0)
        self.text_color = (0.0, 0.0, 0.0)
        self.line_color = (1.0, 1.0, 1.0)
        self.highlight_color = (1.0, 0.0, 0.0)
        self.class_benign_color = (0.0, 0.7, 0.0)
        self.class_attack_color = (0.7, 0.0, 0.0)
        self.path_highlight_color = (1.0, 1.0, 0.0)
        self.path_line_color = (1.0, 0.5, 0.0)

        # Progressive coloring system
        self.node_visit_counts = {}
        self.node_base_colors = {}
        self.max_visits = 10
        
        # Base colors for the three color families
        self.color_families = {
            'blue': {
                'light': (1.0, 1.0, 1.0),
                'dark': (0.0, 0.2, 0.8)
            },
            'yellow': {
                'light': (1.0, 1.0, 1.0),
                'dark': (0.8, 0.6, 0.0)
            },
            'purple': {
                'light': (1.0, 1.0, 1.0),
                'dark': (0.5, 0.0, 0.8)
            }
        }
        
        self.leaf_color_families = {
            'benign': {
                'light': (0.9, 1.0, 0.9),
                'dark':  (0.0, 0.5, 0.0)
            },
            'ddos': {
                'light': (1.0, 0.9, 0.9),
                'dark':  (0.5, 0.0, 0.0)
            }
        }

        # Tree metrics and layout
        self.tree_height = 0
        self.node_positions = {}
        self.level_widths = {}

        # Path highlighting
        self.highlighted_paths = set()
        self.current_path = []
        self.path_lock = threading.Lock()

        # Font
        self.font = None
        
        # Auto-redraw mechanism
        self.needs_redraw = False
        self.redraw_timer = None

        # Add tooltip functionality
        self.mouse_x = 0
        self.mouse_y = 0
        self.hovered_node = None
        self.tooltip_text = ""
        self.show_tooltip = False
    
        self.node_timers = {}  # Dictionary to track individual timers for each node (key: node_id)
        self.node_timer_active = {}  # Dictionary to track if timer is active for each node
        self.global_node_timer = 2.0  # Global timer value in SECONDS (2 seconds)
    
        # Edge highlighting system
        self.edge_timers = {}  # Dictionary to track individual timers for each edge (key: (parent_id, child_id))
        self.edge_visit_counts = {}  # Dictionary to track visit counts for each edge
        self.global_edge_timer = 2.0  # Global timer value in SECONDS (2 seconds)
        self.last_time = 0  # For tracking time in idle function
        self.edge_timer_active = {}  # Dictionary to track if timer is active for each edge

        # Timer input functionality
        self.timer_input_active = False
        self.timer_input_text = "2"  # Default timer value
        self.timer_input_cursor = len(self.timer_input_text)
        self.timer_input_box_width = 120
        self.timer_input_box_height = 25
        self.timer_input_box_x = self.screen_width - self.timer_input_box_width - 10  # Top right corner
        self.timer_input_box_y = self.screen_height - self.timer_input_box_height - 10  # Top right corner
        self.show_timer_input = True
    
    def draw_timer_input_box(self):
        """Draw the timer input box and handle its display - positioned in top right corner."""
        if not self.show_timer_input:
            return
        
        # Update position to always be in top right corner (in case of screen resize)
        box_x = self.screen_width - self.timer_input_box_width - 10
        box_y = self.screen_height - self.timer_input_box_height - 10
        box_width = self.timer_input_box_width
        box_height = self.timer_input_box_height
        
        # Update stored position
        self.timer_input_box_x = box_x
        self.timer_input_box_y = box_y
        
        # Draw input box background
        if self.timer_input_active:
            glColor4f(0.9, 0.9, 0.9, 0.9)  # Light gray when active
        else:
            glColor4f(0.7, 0.7, 0.7, 0.8)  # Darker gray when inactive
        
        glBegin(GL_QUADS)
        glVertex2f(box_x, box_y)
        glVertex2f(box_x + box_width, box_y)
        glVertex2f(box_x + box_width, box_y + box_height)
        glVertex2f(box_x, box_y + box_height)
        glEnd()
        
        # Draw input box border
        if self.timer_input_active:
            glColor4f(0.0, 0.5, 1.0, 1.0)  # Blue border when active
            glLineWidth(2.0)
        else:
            glColor4f(0.5, 0.5, 0.5, 1.0)  # Gray border when inactive
            glLineWidth(1.0)
        
        glBegin(GL_LINE_LOOP)
        glVertex2f(box_x, box_y)
        glVertex2f(box_x + box_width, box_y)
        glVertex2f(box_x + box_width, box_y + box_height)
        glVertex2f(box_x, box_y + box_height)
        glEnd()
        
        # Draw label ABOVE the input box (since it's in top right corner)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        label_text = "Timer (sec):"
        label_width = len(label_text) * 7  # Estimate label width
        label_x = box_x + (box_width - label_width) / 2  # Center label above box
        self.display_text(label_text, label_x, box_y + box_height + 15)
        
        # Draw input text
        if self.timer_input_active:
            glColor4f(0.0, 0.0, 0.0, 1.0)  # Black text when active
        else:
            glColor4f(0.3, 0.3, 0.3, 1.0)  # Dark gray text when inactive
        
        # Center text vertically in the box
        text_y = box_y + box_height / 2 - 5
        self.display_text(self.timer_input_text, box_x + 5, text_y)
        
        # Draw cursor if active
        if self.timer_input_active:
            cursor_x = box_x + 5 + len(self.timer_input_text[:self.timer_input_cursor]) * 6
            glColor4f(0.0, 0.0, 0.0, 1.0)
            glBegin(GL_LINES)
            glVertex2f(cursor_x, box_y + 3)
            glVertex2f(cursor_x, box_y + box_height - 3)
            glEnd()
    
    def update_timer_values(self):
        """Update both global timer values from input text - converting from seconds to internal format - INT ONLY."""
        try:
            # Parse as integer only
            new_timer_value_seconds = int(self.timer_input_text)
            if new_timer_value_seconds > 0:  # Ensure positive value
                self.global_node_timer = float(new_timer_value_seconds)  # Convert to float for internal use
                self.global_edge_timer = float(new_timer_value_seconds)  # Convert to float for internal use
            else:
                # If invalid, reset to default
                self.timer_input_text = "2"
                self.global_node_timer = 2.0
                self.global_edge_timer = 2.0
        except ValueError:
            # If conversion fails, reset to default
            self.timer_input_text = "2"
            self.global_node_timer = 2.0
            self.global_edge_timer = 2.0

        # Update cursor position to end of text
        self.timer_input_cursor = len(self.timer_input_text)
    
    def is_point_in_timer_input_box(self, x, y):
        """Check if a point is inside the timer input box."""
        return (self.timer_input_box_x <= x <= self.timer_input_box_x + self.timer_input_box_width and
                self.timer_input_box_y <= y <= self.timer_input_box_y + self.timer_input_box_height)
    
    def update_node_timers(self, delta_time):
        """Update all active node timers and reset nodes when timer expires - delta_time in milliseconds."""
        nodes_to_reset = []
        delta_seconds = delta_time / 1000.0  # Convert milliseconds to seconds
        
        for node_id in list(self.node_timers.keys()):
            if self.node_timer_active.get(node_id, False):
                # Increment timer (in seconds)
                self.node_timers[node_id] += delta_seconds
                
                # Check if timer has reached global timer value (in seconds)
                if self.node_timers[node_id] >= self.global_node_timer:
                    # Timer expired - reset this node
                    nodes_to_reset.append(node_id)
        
        # Reset expired nodes
        for node_id in nodes_to_reset:
            self.node_visit_counts[node_id] = 0
            self.node_timers[node_id] = 0.0
            self.node_timer_active[node_id] = False
        
        # Trigger redraw if any nodes were reset
        if nodes_to_reset:
            self.schedule_redraw()

    
    def update_edge_timers(self, delta_time):
        """Update all active edge timers and reset edges when timer expires - delta_time in milliseconds."""
        edges_to_reset = []
        delta_seconds = delta_time / 1000.0  # Convert milliseconds to seconds
        
        for edge_key in list(self.edge_timers.keys()):
            if self.edge_timer_active.get(edge_key, False):
                # Increment timer (in seconds)
                self.edge_timers[edge_key] += delta_seconds
                
                # Check if timer has reached global timer value (in seconds)
                if self.edge_timers[edge_key] >= self.global_edge_timer:
                    # Timer expired - reset this edge
                    edges_to_reset.append(edge_key)
        
        # Reset expired edges
        for edge_key in edges_to_reset:
            self.edge_visit_counts[edge_key] = 0
            self.edge_timers[edge_key] = 0.0
            self.edge_timer_active[edge_key] = False
        
        # Trigger redraw if any edges were reset
        if edges_to_reset:
            self.schedule_redraw()
        
    
    def passive_mouse_motion(self, x, y):
        """Handle passive mouse motion for hover detection."""
        # Convert screen coordinates to world coordinates
        self.mouse_x = x
        self.mouse_y = y
        
        # Convert GLUT coordinates (origin top-left) to OpenGL coordinates (origin bottom-left)
        opengl_y = self.screen_height - y
        
        # Find node under mouse cursor
        hovered_node = self.get_node_at_position(x, opengl_y)
        
        if hovered_node != self.hovered_node:
            self.hovered_node = hovered_node
            if hovered_node:
                self.tooltip_text = getattr(hovered_node, 'name', '')
                self.show_tooltip = True
            else:
                self.show_tooltip = False
            glutPostRedisplay()
    
    def get_node_at_position(self, screen_x, screen_y):
        """Find the node at the given screen position."""
        if not self.root or not self.node_positions:
            return None
        
        return self._check_node_at_position(self.root, screen_x, screen_y)
    
    def _check_node_at_position(self, node, screen_x, screen_y):
        """Recursively check if a node contains the given screen position."""
        node_id = id(node)
        if node_id not in self.node_positions:
            return None
        
        # Get node position in world coordinates
        world_x, world_y = self.node_positions[node_id]
        
        # Convert to screen coordinates
        node_screen_x = world_x + self.scroll_x
        node_screen_y = world_y + self.scroll_y
        
        # Get node dimensions
        node_width = self.get_node_rect_width(node)
        node_height = self.get_node_rect_height(node)
        
        # Check if mouse is within node bounds
        left = node_screen_x - node_width / 2
        right = node_screen_x + node_width / 2
        top = node_screen_y + node_height / 2
        bottom = node_screen_y - node_height / 2
        
        if (screen_x >= left and screen_x <= right and 
            screen_y >= bottom and screen_y <= top):
            return node
        
        # Check children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                result = self._check_node_at_position(child, screen_x, screen_y)
                if result:
                    return result
        
        return None

    def draw_tooltip(self):
        """Draw tooltip when hovering over a node at zoom < 1.4."""
        if not self.show_tooltip or not self.hovered_node or self.zoom >= 1.4:
            return
        
        if not self.tooltip_text:
            return
        
        # Calculate tooltip position
        tooltip_x = self.mouse_x + 10  # Offset from mouse
        tooltip_y = self.screen_height - self.mouse_y - 10  # Convert and offset from mouse
        
        # Ensure tooltip stays within screen bounds
        tooltip_width = len(self.tooltip_text) * 7 + 20  # Estimate width
        tooltip_height = 25
        
        if tooltip_x + tooltip_width > self.screen_width:
            tooltip_x = self.screen_width - tooltip_width - 5
        if tooltip_y - tooltip_height < 0:
            tooltip_y = tooltip_height + 5
        
        # Draw tooltip background
        glColor4f(0.0, 0.0, 0.0, 0.8)  # Semi-transparent black
        glBegin(GL_QUADS)
        glVertex2f(tooltip_x - 10, tooltip_y - 15)
        glVertex2f(tooltip_x + tooltip_width - 10, tooltip_y - 15)
        glVertex2f(tooltip_x + tooltip_width - 10, tooltip_y + 10)
        glVertex2f(tooltip_x - 10, tooltip_y + 10)
        glEnd()
        
        # Draw tooltip border
        glColor4f(1.0, 1.0, 1.0, 0.8)  # White border
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(tooltip_x - 10, tooltip_y - 15)
        glVertex2f(tooltip_x + tooltip_width - 10, tooltip_y - 15)
        glVertex2f(tooltip_x + tooltip_width - 10, tooltip_y + 10)
        glVertex2f(tooltip_x - 10, tooltip_y + 10)
        glEnd()
        
        # Draw tooltip text
        glColor4f(1.0, 1.0, 1.0, 1.0)  # White text
        self.display_text(self.tooltip_text, tooltip_x, tooltip_y)

    def set_tree(self, root_node):
        """Set the root node of the tree to visualize."""
        self.root = root_node
        if root_node:
            self.calculate_node_positions()
            # Initialize node colors and visit counts
            self._initialize_node_properties(root_node)
            # Calculate class distribution for each subtree
            self._calculate_subtree_class_distributions(root_node)

    def _initialize_node_properties(self, node):
        """Initialize node properties like colors and visit counts."""
        node_id = id(node)
        
        # Initialize visit count
        if node_id not in self.node_visit_counts:
            self.node_visit_counts[node_id] = 0
        
        # Initialize subtree class distribution
        if not hasattr(self, 'subtree_class_distributions'):
            self.subtree_class_distributions = {}
        
        # Assign base color if not already assigned
        if node_id not in self.node_base_colors:
            name = getattr(node, 'name', '')
            if name.startswith("Class:"):
                # Leaf nodes get special colors based on class
                if "benign" in name.lower():
                    self.node_base_colors[node_id] = 'benign'
                elif "attack" in name.lower() or "ddos" in name.lower():
                    self.node_base_colors[node_id] = 'ddos'
                else:
                    # Default to blue for unknown classes
                    self.node_base_colors[node_id] = 'blue'
            else:
                # Internal nodes get random color assignment
                color_keys = list(self.color_families.keys())
                self.node_base_colors[node_id] = random.choice(color_keys)
        
        # Recursively initialize children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._initialize_node_properties(child)

    def _calculate_subtree_class_distributions(self, node):
        """Calculate class distribution for each subtree."""
        node_id = id(node)
        name = getattr(node, 'name', '')
        
        # Initialize distribution dictionary
        distribution = {'ddos': 0, 'benign': 0, 'other': 0}
        
        if name.startswith("Class:"):
            # Leaf node - count itself
            if "benign" in name.lower():
                distribution['benign'] = 1
            elif "attack" in name.lower() or "ddos" in name.lower():
                distribution['ddos'] = 1
            else:
                distribution['other'] = 1
        else:
            # Internal node - sum distributions from children
            if hasattr(node, 'children') and node.children:
                for child in node.children:
                    child_dist = self._calculate_subtree_class_distributions(child)
                    distribution['ddos'] += child_dist['ddos']
                    distribution['benign'] += child_dist['benign']
                    distribution['other'] += child_dist['other']
        
        # Store the distribution for this node
        self.subtree_class_distributions[node_id] = distribution
        return distribution
    
    def _get_arc_color_based_on_distribution(self, parent_node, child_node):
        """Get arc color based on the child's subtree class distribution - with timer-based white override."""
        child_id = id(child_node)
        parent_id = id(parent_node)
        edge_key = (parent_id, child_id)
        
        # Check edge visit count first
        edge_visits = self.edge_visit_counts.get(edge_key, 0)
        
        # If edge visit count is 0 (either never visited or timer expired), return white
        if edge_visits == 0:
            return (1.0, 1.0, 1.0)  # White color
        
        # Check if parent has been visited at least once
        parent_visits = self.node_visit_counts.get(parent_id, 0)
        if parent_visits == 0:
            # Not visited yet, use default line color
            return self.line_color
        
        # Get child's subtree distribution
        if child_id not in self.subtree_class_distributions:
            return self.line_color
        
        distribution = self.subtree_class_distributions[child_id]
        total_leaves = distribution['ddos'] + distribution['benign'] + distribution['other']
        
        if total_leaves == 0:
            return self.line_color
        
        # Calculate proportions
        ddos_ratio = distribution['ddos'] / total_leaves
        benign_ratio = distribution['benign'] / total_leaves
        
        # Define base colors for interpolation
        ddos_color = (0.9, 0.1, 0.1)    # Red for DDOS
        benign_color = (0.1, 0.8, 0.1)  # Green for benign
        
        # Linear interpolation between colors based on proportions
        # Each component (R, G, B) is calculated as weighted sum
        r = ddos_ratio * ddos_color[0] + benign_ratio * benign_color[0]
        
        g = ddos_ratio * ddos_color[1] + benign_ratio * benign_color[1]
        
        b = ddos_ratio * ddos_color[2] + benign_ratio * benign_color[2]
        
        # Ensure color components are within valid range [0.0, 1.0]
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
        
        return (r, g, b)


    def get_adaptive_spacing(self):
        """Calculate adaptive spacing intre noduri cu prevenirea suprapunerii imbunatatita si reducere la zoom out."""
        # Distanta de baza foarte redusa
        base_spacing = 4
        
        # Calculeaza dimensiunea medie a nodurilor pentru a preveni suprapunerea
        if self.root and self.node_positions:
            # Estimeaza dimensiunea nodului la zoom-ul curent
            sample_node_width = self.get_node_rect_width(self.root) * self.zoom
            sample_node_height = self.get_node_rect_height(self.root) * self.zoom
            
            # Distanta minima necesara pentru a evita suprapunerea
            min_required_spacing = max(sample_node_width * 0.05, sample_node_height * 0.05, 2)  # REDUS
        else:
            min_required_spacing = 2
        
        # Adapteaza spacing-ul in functie de zoom cu prevenirea suprapunerii - mai agresiv la zoom out
        if self.zoom >= 1.0:
            spacing = max(base_spacing, min_required_spacing)
        elif self.zoom >= 0.8:
            spacing = max(base_spacing * 1.1, min_required_spacing)  
        elif self.zoom >= 0.6:
            spacing = max(base_spacing * 1.2, min_required_spacing)  
        elif self.zoom >= 0.4:
            spacing = max(base_spacing * 1.3, min_required_spacing) 
        elif self.zoom >= 0.3:
            spacing = max(base_spacing * 1.4, min_required_spacing)  
        elif self.zoom >= 0.2:
            spacing = max(base_spacing * 1.5, min_required_spacing)  
        elif self.zoom >= 0.15:
            spacing = max(base_spacing * 1.6, min_required_spacing)  
        elif self.zoom >= 0.08:
            spacing = max(base_spacing * 1.8, min_required_spacing)  
        else:
            # La zoom foarte mic, spacing minim pentru compactitate extrema
            spacing = max(base_spacing * 2.0, min_required_spacing)  
        
        return spacing

    def get_adaptive_level_height(self):
        """Calculeaza inaltimea adaptiva intre niveluri cu prevenirea suprapunerii si mai buna scalare la zoom mare."""
        # Inaltimea de baza
        base_level_height = 80  # Marit de la 60 pentru spatiu mai bun la zoom mare
        
        # Calculeaza inaltimea necesara pentru a evita suprapunerea nodurilor
        if self.root:
            sample_node_height = self.get_node_rect_height(self.root)
            min_required_height = sample_node_height * 1.5  # Marit factorul pentru spatiu mai bun
        else:
            min_required_height = 40  # Marit de la 30
        
        # Scalare mai buna pentru zoom mare
        if self.zoom >= 2.0:
            return max(base_level_height * 1.4, min_required_height)  # Spatiu extra la zoom foarte mare
        elif self.zoom >= 1.5:
            return max(base_level_height * 1.2, min_required_height)  # Spatiu extra la zoom mare
        elif self.zoom >= 1.0:
            return max(base_level_height, min_required_height)
        elif self.zoom >= 0.8:
            return max(base_level_height * 0.9, min_required_height)
        elif self.zoom >= 0.6:
            return max(base_level_height * 0.8, min_required_height)
        elif self.zoom >= 0.4:
            return max(base_level_height * 0.7, min_required_height)
        elif self.zoom >= 0.3:
            return max(base_level_height * 0.6, min_required_height)
        elif self.zoom >= 0.2:
            return max(base_level_height * 0.5, min_required_height)
        elif self.zoom >= 0.1:
            return max(base_level_height * 0.4, min_required_height)
        elif self.zoom >= 0.05:
            return max(base_level_height * 0.35, min_required_height)
        else:
            return max(base_level_height * 0.3, min_required_height)

    def get_line_width_multiplier(self):
        """Calculate line width multiplier based on zoom level. Lower zoom = thicker lines."""
        # At max zoom out (0.2), lines should be thickest (multiplier = 3.0)
        # At normal zoom (1.0), lines should be normal (multiplier = 1.0)
        # Linear interpolation
        min_zoom = self.max_zoom_out
        normal_zoom = 1.0
        max_multiplier = 3.0
        min_multiplier = 1.0
        
        if self.zoom >= normal_zoom:
            return min_multiplier
        else:
            # Linear interpolation between min_zoom and normal_zoom
            zoom_range = normal_zoom - min_zoom
            current_range = self.zoom - min_zoom
            progress = current_range / zoom_range
            return max_multiplier + (min_multiplier - max_multiplier) * progress

    def calculate_node_positions(self):
        """Calculate positions for all nodes cu distante adaptive si inaltimi foarte reduse la zoom out."""
        if not self.root:
            return
            
        self.node_positions = {}
        
        # First pass: calculate the width needed for each subtree cu distante adaptive
        subtree_widths = {}
        self._calculate_subtree_widths(self.root, subtree_widths)
        
        # Second pass: assign positions based on calculated widths
        root_width = subtree_widths[id(self.root)]
        start_x = 0
        start_y = self.screen_height - 100
        
        # Inaltimea intre niveluri FOARTE ADAPTIVA - se reduce semnificativ la zoom out
        adaptive_level_height = self.get_adaptive_level_height()
        
        self._assign_positions(self.root, start_x, start_y, root_width, subtree_widths, adaptive_level_height)
        
        # Center the entire tree
        if self.node_positions:
            min_x = min(pos[0] for pos in self.node_positions.values())
            max_x = max(pos[0] for pos in self.node_positions.values())
            tree_width = max_x - min_x
            
            # Calculate offset to center the tree
            center_offset = (self.screen_width / 2) - (min_x + tree_width / 2)
            
            # Apply centering offset
            for node_id in self.node_positions:
                x, y = self.node_positions[node_id]
                centered_x = x + center_offset
                self.node_positions[node_id] = (centered_x, y)

    def _assign_positions(self, node, x, y, available_width, subtree_widths, level_height, level=0):
        """Assign actual positions to nodes cu spacing imbunatatit si prevenirea suprapunerii."""
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
        
        # Calculate positions for children cu spacing imbunatatit
        child_y = y - level_height
        current_x = x
        adaptive_distance = self.get_adaptive_spacing()
        
        # Verifica daca copiii se suprapun si ajusteaza daca e necesar
        total_children_width = sum(subtree_widths[id(child)] for child in children)
        total_spacing_needed = (num_children - 1) * adaptive_distance
        total_required_width = total_children_width + total_spacing_needed
        
        # Daca latimea disponibila este mai mica decat cea necesara reduce spacing-ul inteligent
        if total_required_width > available_width and num_children > 1:
            # Calculeaza spacing-ul maxim posibil fara suprapunere
            max_possible_spacing = (available_width - total_children_width) / (num_children - 1)
            # Asigura un minimum absolut pentru prevenirea suprapunerii complete
            adaptive_distance = max(max_possible_spacing, 1.5)  # Minimum 1.5 pixels spacing
        
        for i, child in enumerate(children):
            child_width = subtree_widths[id(child)]
            
            # Position child in its allocated space
            self._assign_positions(child, current_x, child_y, child_width, subtree_widths, level_height, level + 1)
            
            # Move to next child position cu spacing ajustat
            current_x += child_width
            if i < num_children - 1:  # Add adaptive spacing between siblings
                current_x += adaptive_distance
    
    def get_node_color(self, node):
        """Get the color for a node based on its type and visit count - with timer-based white override."""
        node_id = id(node)
        
        # Check node visit count first
        visit_count = self.node_visit_counts.get(node_id, 0)
        
        # If visit count is 0 (either never visited or timer expired), return white
        if visit_count == 0:
            return (1.0, 1.0, 1.0)  # White color
        
        base_color_key = self.node_base_colors.get(node_id, 'blue')
        
        # Calculate color interpolation based on visit count
        progress = min(visit_count / self.max_visits, 1.0)
        
        # Check if it's a leaf node with special coloring
        name = getattr(node, 'name', '')
        if name.startswith("Class:"):
            if base_color_key in self.leaf_color_families:
                color_family = self.leaf_color_families[base_color_key]
            else:
                # Fallback to regular color families
                color_family = self.color_families.get(base_color_key, self.color_families['blue'])
        else:
            color_family = self.color_families.get(base_color_key, self.color_families['blue'])
        
        # Interpolate between light and dark colors
        light_color = color_family['light']
        dark_color = color_family['dark']
        
        # Linear interpolation
        r = light_color[0] + (dark_color[0] - light_color[0]) * progress
        g = light_color[1] + (dark_color[1] - light_color[1]) * progress
        b = light_color[2] + (dark_color[2] - light_color[2]) * progress
        
        return (r, g, b)
    
    def is_node_in_highlighted_path(self, node):
        """Check if a node is part of any highlighted path."""
        with self.path_lock:
            return id(node) in self.highlighted_paths
    
    def get_adaptive_text(self, text, max_width_pixels, zoom_level):
        """Adapteaza textul in functie de nivelul de zoom si latimea disponibila - fara puncte."""
        if not text:
            return ""
        
        # Estimeaza latimea unui caracter la zoom-ul curent (mai precis)
        char_width = max(4 * zoom_level, 1.5)
        max_chars = int(max_width_pixels / char_width)
        
        if max_chars <= 0:
            return ""
        
        # Scalare text in functie de zoom - fara puncte
        if zoom_level >= 0.7:
            # Text complet la zoom mare
            if len(text) <= max_chars:
                return text
            else:
                return text[:max_chars]
        elif zoom_level >= 0.4:
            # Text prescurtat pentru zoom mediu
            max_chars = min(max_chars, 25)
            if len(text) <= max_chars:
                return text
            else:
                return text[:max_chars]
        elif zoom_level >= 0.2:
            # Text foarte prescurtat pentru zoom mic
            max_chars = min(max_chars, 15)
            if len(text) <= max_chars:
                return text
            else:
                # Incearca sa pastreze partea importanta
                if "Class:" in text:
                    short_text = text.replace("Class:", "C:")
                    if len(short_text) <= max_chars:
                        return short_text
                    else:
                        return short_text[:max_chars]
                elif "<=" in text:
                    # Pentru conditii pastreaza partea principala
                    feature_part = text.split("<=")[0].strip()
                    if len(feature_part) <= max_chars:
                        return feature_part
                    else:
                        return feature_part[:max_chars]
                else:
                    return text[:max_chars]
        elif zoom_level >= 0.1:
            # Pentru zoom foarte mic doar cuvinte cheie
            max_chars = min(max_chars, 10)
            if "Class:" in text:
                class_part = text.replace("Class:", "").strip()
                words = class_part.split()
                if words:
                    first_word = words[0]
                    return first_word[:max_chars] if len(first_word) > max_chars else first_word
            elif "<=" in text:
                feature_part = text.split("<=")[0].strip()
                return feature_part[:max_chars] if len(feature_part) > max_chars else feature_part
            else:
                words = text.split()
                if words:
                    first_word = words[0]
                    return first_word[:max_chars] if len(first_word) > max_chars else first_word
                else:
                    return text[:max_chars] if len(text) > 0 else ""
        else:
            # Pentru zoom extrem de mic
            if max_chars >= 2:
                if "Class:" in text:
                    class_name = text.replace("Class:", "").strip()
                    if class_name:
                        return class_name[0].upper()
                elif "<=" in text:
                    feature_name = text.split("<=")[0].strip()
                    words = feature_name.split()
                    if words:
                        initials = ''.join([w[0].upper() for w in words[:2]])
                        return initials[:max_chars]
                else:
                    words = text.split()
                    if words:
                        return words[0][0].upper()
                    else:
                        return text[0].upper() if text else ""
            else:
                if text:
                    return text[0].upper()
                else:
                    return ""
        
        return text[:max_chars] if text else ""

    def display_text_scaled(self, text, x, y, max_width, zoom_level):
        """Display text scalat cu zoom-ul si limitare de latime fara puncte si fara distantare la zoom-in."""
        if not text or zoom_level < 0.02:
            return
        
        # Adapteaza textul sa incapa in latimea disponibila
        adapted_text = self.get_adaptive_text(text, max_width, zoom_level)
        if not adapted_text:
            return
        
        # Calculeaza pozitia exacta pentru a centra textul - foloseste latimea font-ului standard
        estimated_text_width = len(adapted_text) * 6  # Latime fixa standard pentru caracter
        centered_x = x - estimated_text_width / 2
        
        glRasterPos2f(centered_x, y)
        
        if self.font is None:
            return
        
        try:
            # Pentru zoom foarte mic, simuleaza font mai mic prin sarirea caracterelor
            if zoom_level < 0.08:
                # Afiseaza doar fiecare al 2-lea sau 3-lea caracter pentru efect de "font mic"
                step = max(1, int(0.15 / max(zoom_level, 0.01)))
                displayed_text = adapted_text[::step]
            elif zoom_level < 0.15:
                # Afiseaza majoritatea caracterelor
                displayed_text = adapted_text
            else:
                displayed_text = adapted_text
            
            # Afiseaza caracterele FARA spacing custom - lasa font-ul sa gestioneze spacing-ul
            for char in displayed_text:
                glutBitmapCharacter(self.font, ord(char))
                
        except:
            pass

    def draw_line(self, x1, y1, x2, y2, is_path_line=False, parent_node=None, child_node=None):
        """Draw a line between two points with adaptive coloring based on visits and distribution."""
        line_width_multiplier = self.get_line_width_multiplier()
        
        if is_path_line:
            # Path lines always use path color
            glColor3f(*self.path_line_color)
            glLineWidth(4.0 * line_width_multiplier)
        else:
            # Use distribution-based coloring ONLY if parent has been visited
            if parent_node is not None and child_node is not None:
                parent_id = id(parent_node)
                parent_visits = self.node_visit_counts.get(parent_id, 0)
                
                if parent_visits >= 1:
                    # Parent has been visited, use distribution-based coloring
                    arc_color = self._get_arc_color_based_on_distribution(parent_node, child_node)
                    glColor3f(*arc_color)
                else:
                    # Parent not visited, use default color
                    glColor3f(*self.line_color)
            else:
                # No nodes provided, use default color
                glColor3f(*self.line_color)
            
            glLineWidth(2.0 * line_width_multiplier)
        
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()
    
    
    def schedule_redraw(self):
        """Schedule a redraw of the visualization."""
        self.needs_redraw = True
        glutPostRedisplay()

    def check_redraw(self):
        """Check if a redraw is needed and reset the flag."""
        if self.needs_redraw:
            self.needs_redraw = False
            return True
        return False

    def idle(self):
        """Idle function to handle both edge and node timer updates."""
        
        current_time = time.time() * 1000  # Convert to milliseconds
        
        if self.last_time == 0:
            self.last_time = current_time
            return
        
        delta_time = current_time - self.last_time
        self.last_time = current_time
        
        # Update both edge and node timers
        self.update_edge_timers(delta_time)
        self.update_node_timers(delta_time)

    def display(self):
        """Main display function with zoom optimizations and timer input."""
        # Check if we need to redraw
        self.check_redraw()
        
        # Apply zoom-specific rendering optimizations
        self.optimize_rendering_for_zoom()
        
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.root:
            # Draw the tree
            self.draw_tree()
            
            # Draw tooltip (only when zoom < 1.0)
            self.draw_tooltip()
            
            # Draw help text (only if zoom allows)
            self.draw_help_text()
            
            # Draw zoom level indicator
            self.draw_zoom_indicator()
        
        # Draw timer input box
        self.draw_timer_input_box()
            
        glutSwapBuffers()
    
    def draw_help_text(self):
        """Draw help text for navigation - DOAR la zoom >= 1.0 cu timer info in seconds - INT ONLY."""
        if self.zoom < 1.0:
            return  # Nu afisa help text sub zoom 1.0
            
        text_alpha = self.get_text_alpha()
        if text_alpha > 0.01:  # Only draw help text if visible
            glColor4f(1.0, 1.0, 1.0, text_alpha)
            help_text = [
                "Navigation Controls:",
                "- Mouse Drag: Pan view",
                "- Mouse Wheel: Zoom in/out",
                f"- Current Zoom: {self.zoom:.2f}",
                "",
                "Timer Controls:",
                f"- T: Toggle timer input (Current: {int(self.global_node_timer)}s)",
                "- Click timer box to edit value",
                "- Enter to confirm, Esc to cancel",
                "- Accepts only integer values (e.g., 1, 2, 5)",
                "",
                "Node Coloring:",
                "- Blue/Yellow/Purple: Random assignment",
                "- Light to Dark: Visit frequency",
                "- Numbers in (): Visit count",
                "",
                "Arc Coloring (when visited):",
                "- Green: Predominantly Benign subtree",
                "- Red: Predominantly DDOS subtree", 
                "- Orange/Yellow: Mixed subtree",
                "",
                "Zoom Features:",
                "- Text visible only at zoom >= 1.0",
                "- Lines get thicker when zoomed out"
            ]
            
            x = 10
            y = self.screen_height - 20
            for line in help_text:
                self.display_text(line, x, y)
                y -= 15

    def display_text(self, text, x, y):
        """Display text at the given position"""
        scaled_x = x
        scaled_y = y
        
        glRasterPos2f(scaled_x, scaled_y)
        
        if self.font is None:
            return
            
        try:
            # Pentru textul general (help, zoom indicator), foloseste adaptare fara puncte
            if self.zoom < 0.3:
                # Prescurteaza textul pentru zoom mic fara puncte
                max_len = max(5, int(25 * self.zoom / 0.3))
                display_text = text[:max_len] if len(text) > max_len else text
            else:
                display_text = text
            
            # Pentru zoom foarte mic, prescurtare mai agresiva
            if self.zoom < 0.15:
                max_len = max(3, int(10 * self.zoom / 0.15))
                display_text = display_text[:max_len] if len(display_text) > max_len else display_text
            
            # Simuleaza font mai mic prin caractere mai rare la zoom mic
            if self.zoom < 0.1:
                # Afiseaza doar fiecare al 2-lea caracter
                display_text = display_text[::2]
            
            # Afiseaza textul FARA spacing manual - lasa font-ul sa gestioneze spacing-ul
            for char in display_text:
                glutBitmapCharacter(self.font, ord(char))
        except:
            pass
    
    def mouse(self, button, state, x, y):
        """Handle mouse input cu zoom extins si zoom-to-mouse-position si timer input."""
        # Convert y coordinate to OpenGL coordinates
        opengl_y = self.screen_height - y
        
        # Check if click is on timer input box
        if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
            if self.is_point_in_timer_input_box(x, opengl_y):
                self.timer_input_active = True
                glutPostRedisplay()
                return
            else:
                # Clicked outside input box, deactivate it and update timer values
                if self.timer_input_active:
                    self.timer_input_active = False
                    self.update_timer_values()
                    glutPostRedisplay()
        
        # Update mouse position for zoom calculations
        self.mouse_x = x
        self.mouse_y = opengl_y
        
        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                self.dragging = True
                self.last_x = x
                self.last_y = y
            else:
                self.dragging = False
        elif button == 3:  # Mouse wheel up
            self.zoom_at_mouse_position(True)
        elif button == 4:  # Mouse wheel down
            self.zoom_at_mouse_position(False)
    
    def keyboard(self, key, x, y):
        """Handle keyboard input for additional controls cu zoom-to-center si timer input - supports decimal input."""
        # Handle timer input when active
        if self.timer_input_active:
            if key == b'\r' or key == b'\n':  # Enter key
                self.timer_input_active = False
                self.update_timer_values()
                glutPostRedisplay()
                return
            elif key == b'\x08':  # Backspace
                if self.timer_input_cursor > 0:
                    self.timer_input_text = (self.timer_input_text[:self.timer_input_cursor-1] + 
                                        self.timer_input_text[self.timer_input_cursor:])
                    self.timer_input_cursor -= 1
                    glutPostRedisplay()
                return
            elif key == b'\x7f':  # Delete key
                if self.timer_input_cursor < len(self.timer_input_text):
                    self.timer_input_text = (self.timer_input_text[:self.timer_input_cursor] + 
                                        self.timer_input_text[self.timer_input_cursor+1:])
                    glutPostRedisplay()
                return
            elif key.isdigit() or key == b'.':  # Numeric input and decimal point
                char = key.decode('utf-8')
                # Allow only one decimal point
                if char == '.' and '.' in self.timer_input_text:
                    return
                self.timer_input_text = (self.timer_input_text[:self.timer_input_cursor] + 
                                    char + 
                                    self.timer_input_text[self.timer_input_cursor:])
                self.timer_input_cursor += 1
                glutPostRedisplay()
                return
            elif key == b'\x1b':  # Escape key - exit input mode
                self.timer_input_active = False
                glutPostRedisplay()
                return
        
        # Handle regular keyboard shortcuts
        if key == b'r' or key == b'R':
            # Reset view - recalculate positions to fit screen
            self.zoom = 1.0
            self.scroll_x = 0
            self.scroll_y = 0
            self.calculate_node_positions()
            glutPostRedisplay()
        elif key == b'+' or key == b'=':
            # Zoom in at current mouse position (or screen center if no mouse movement yet)
            if not hasattr(self, 'mouse_x') or self.mouse_x is None:
                self.mouse_x = self.screen_width / 2
                self.mouse_y = self.screen_height / 2
            self.zoom_at_mouse_position(True)
        elif key == b'-' or key == b'_':
            # Zoom out at current mouse position (or screen center if no mouse movement yet)
            if not hasattr(self, 'mouse_x') or self.mouse_x is None:
                self.mouse_x = self.screen_width / 2
                self.mouse_y = self.screen_height / 2
            self.zoom_at_mouse_position(False)
        elif key == b't' or key == b'T':
            # Toggle timer input box visibility
            self.show_timer_input = not self.show_timer_input
            glutPostRedisplay()
        elif key == b'\x1b':  # Escape key
            print("Exiting visualization...")
            sys.exit(0)
    
    def handle_timer_input_special_keys(self, key):
        """Handle special keys for timer input - INT ONLY version."""
        if not self.timer_input_active:
            return False
        
        if key == 8:  # Backspace
            if self.timer_input_cursor > 0:
                left_part = self.timer_input_text[:self.timer_input_cursor-1]
                right_part = self.timer_input_text[self.timer_input_cursor:]
                self.timer_input_text = left_part + right_part
                self.timer_input_cursor -= 1
            return True
        elif key == 127:  # Delete
            if self.timer_input_cursor < len(self.timer_input_text):
                left_part = self.timer_input_text[:self.timer_input_cursor]
                right_part = self.timer_input_text[self.timer_input_cursor+1:]
                self.timer_input_text = left_part + right_part
            return True
        elif key == 13:  # Enter
            self.update_timer_values()
            self.timer_input_active = False
            return True
        elif key == 27:  # Escape
            # Reset to current timer value
            self.timer_input_text = str(int(self.global_node_timer))
            self.timer_input_cursor = len(self.timer_input_text)
            self.timer_input_active = False
            return True
        elif key == 100:  # Left arrow (GLUT_KEY_LEFT)
            if self.timer_input_cursor > 0:
                self.timer_input_cursor -= 1
            return True
        elif key == 102:  # Right arrow (GLUT_KEY_RIGHT)
            if self.timer_input_cursor < len(self.timer_input_text):
                self.timer_input_cursor += 1
            return True
        
        return False
    
    def handle_timer_input_char(self, char):
        """Handle character input for timer - INT ONLY version."""
        if not self.timer_input_active:
            return False
        
        # Allow only digits
        if char.isdigit():
            # Insert character at cursor position
            left_part = self.timer_input_text[:self.timer_input_cursor]
            right_part = self.timer_input_text[self.timer_input_cursor:]
            self.timer_input_text = left_part + char + right_part
            self.timer_input_cursor += 1
            return True
        
        return False
    
    def highlight_path_for_data(self, data_values, column_names):
        """Highlight the path that would be taken for given data values and update visit counts with timer reset on revisit."""
        if not self.root:
            return
        
        # Clear current path and find new path
        path = self._find_path_for_data(self.root, data_values, column_names)
        
        with self.path_lock:
            # Clear previous highlighted paths
            self.highlighted_paths.clear()
            
            # Add all nodes in the path to highlighted paths and handle visit counts with timers
            for i in range(len(path) - 1):
                parent = path[i]
                child = path[i+1]
                parent_id = id(parent)
                child_id = id(child)
                edge_key = (parent_id, child_id)
                
                # Add to highlighted paths
                self.highlighted_paths.add(parent_id)
                
                # Handle parent node visit count and timer
                prev_node_count = self.node_visit_counts.get(parent_id, 0)
                
                if prev_node_count == 0:
                    # First visit to this node - start timer and set count to 1
                    self.node_visit_counts[parent_id] = 1
                    self.node_timers[parent_id] = 0.0  # Reset timer to 0
                    self.node_timer_active[parent_id] = True  # Activate timer
                else:
                    # Node already visited - increment count and RESET timer to 0 (but keep it active)
                    self.node_visit_counts[parent_id] = prev_node_count + 1
                    self.node_timers[parent_id] = 0.0  # RESET timer to 0 on revisit
                    self.node_timer_active[parent_id] = True  # Ensure timer stays active
                
                # Handle edge visit count and timer
                prev_edge_count = self.edge_visit_counts.get(edge_key, 0)
                
                if prev_edge_count == 0:
                    # First visit to this edge - start timer and set count to 1
                    self.edge_visit_counts[edge_key] = 1
                    self.edge_timers[edge_key] = 0.0  # Reset timer to 0
                    self.edge_timer_active[edge_key] = True  # Activate timer
                else:
                    # Edge already visited - increment count and RESET timer to 0 (but keep it active)
                    self.edge_visit_counts[edge_key] = prev_edge_count + 1
                    self.edge_timers[edge_key] = 0.0  # RESET timer to 0 on revisit
                    self.edge_timer_active[edge_key] = True  # Ensure timer stays active
                
                # Update max visits for color scaling
                current_visits = self.node_visit_counts[parent_id]
                if current_visits > self.max_visits:
                    self.max_visits = current_visits
            
            # Also handle the last node in the path
            if path:
                last_node = path[-1]
                last_node_id = id(last_node)
                self.highlighted_paths.add(last_node_id)
                
                # Handle last node visit count and timer
                prev_count = self.node_visit_counts.get(last_node_id, 0)
                
                if prev_count == 0:
                    # First visit to this node - start timer and set count to 1
                    self.node_visit_counts[last_node_id] = 1
                    self.node_timers[last_node_id] = 0.0  # Reset timer to 0
                    self.node_timer_active[last_node_id] = True  # Activate timer
                else:
                    # Node already visited - increment count and RESET timer to 0 (but keep it active)
                    self.node_visit_counts[last_node_id] = prev_count + 1
                    self.node_timers[last_node_id] = 0.0  # RESET timer to 0 on revisit
                    self.node_timer_active[last_node_id] = True  # Ensure timer stays active
                
                # Update max visits
                if self.node_visit_counts[last_node_id] > self.max_visits:
                    self.max_visits = self.node_visit_counts[last_node_id]
            
            self.current_path = path
        
        # Trigger redraw to show updated colors
        self.schedule_redraw()
    
    def _is_connection_in_path(self, parent_node, child_node):
        """Check if a connection between parent and child is in the highlighted path."""
        with self.path_lock:
            parent_id = id(parent_node)
            child_id = id(child_node)
            return parent_id in self.highlighted_paths and child_id in self.highlighted_paths

    
    def _draw_connections(self, node):
        """Draw connections between nodes with improved arc appearance at high zoom."""
        if not hasattr(node, 'children') or not node.children:
            return

        node_id = id(node)
        if node_id not in self.node_positions:
            return

        # pozitia parintelui (+ scroll)
        parent_x, parent_y = self.node_positions[node_id]
        parent_x += self.scroll_x
        parent_y += self.scroll_y

        # dimensiunea reala a nodului pentru punctele de conectare
        parent_rect_h = self.get_node_rect_height(node)

        for child in node.children:
            child_id = id(child)
            if child_id in self.node_positions:
                # pozitia copilului (+ scroll)
                child_x, child_y = self.node_positions[child_id]
                child_x += self.scroll_x
                child_y += self.scroll_y

                # dimensiunea reala a copilului
                child_rect_h = self.get_node_rect_height(child)

                # verificam daca fac parte dintr-un path subliniat
                is_path_connection = self._is_connection_in_path(node, child)

                # calculam punctele exacte de plecare si de sosire (fundul parintelui → varful copilului)
                start_y = parent_y - (parent_rect_h / 2)
                end_y   = child_y + (child_rect_h / 2)

                # colorarea pe baza distributiei atunci cand parent_visits >= 1
                self.draw_line(
                    parent_x,
                    start_y,
                    child_x,
                    end_y,
                    is_path_connection,  # is_path_line
                    node,                # parent_node
                    child                # child_node
                )

                # apel recursiv pentru subarborele copilului
                self._draw_connections(child)
    
    def draw_node(self, node, x, y, highlighted=False):
        """Draw a tree node cu text scalat - NU afiseaza text sub zoom 1.20."""
        name = getattr(node, 'name', '')
        in_path = self.is_node_in_highlighted_path(node)
        text_alpha = self.get_text_alpha()

        # Alege culoarea
        if highlighted:
            glColor3f(*self.highlight_color)
        else:
            node_color = self.get_node_color(node)
            glColor3f(*node_color)

        # Pregateste liniile de text
        lines = []
        if "<=" in name:    
            lines = [name]
        elif name.startswith("Class:"):
            lines = [name]
        else:
            lines = [name]

        # Calculeaza dimensiunea dreptunghiului
        rect_w = self.get_node_rect_width(node)
        rect_h = self.get_node_rect_height(node)

        # Colturile dreptunghiului
        left   = x - rect_w/2
        right  = x + rect_w/2
        top    = y + rect_h/2
        bottom = y - rect_h/2

        # Deseneaza dreptunghiul
        glBegin(GL_POLYGON)
        glVertex2f(left,  top)
        glVertex2f(right, top)
        glVertex2f(right, bottom)
        glVertex2f(left,  bottom)
        glEnd()

        # Contur cu grosime foarte redusa pentru compactitate
        if in_path:
            glColor3f(1.0, 0.5, 0.0)
            glLineWidth(max(1.8 * self.get_line_width_multiplier(), 1.0))
        else:
            glColor3f(0.8, 0.8, 0.8)
            glLineWidth(max(0.8 * self.get_line_width_multiplier(), 0.5))

        glBegin(GL_LINE_LOOP)
        glVertex2f(left,  top)
        glVertex2f(right, top)
        glVertex2f(right, bottom)
        glVertex2f(left,  bottom)
        glEnd()

        # Textul centrat - DOAR la zoom >= 1.4
        if self.zoom >= 1.4 and text_alpha > 0.008 and rect_w > 6 and rect_h > 6:
            # Set text color with alpha
            text_color_with_alpha = (*self.text_color, text_alpha)
            glColor4f(*text_color_with_alpha)
            
            # Calculeaza dimensiunea scalata a textului cu compactitate maxima
            scaled_line_height = max(8 * self.zoom, 3)
            padding_y = max(1 * self.zoom, 0.3)
            padding_x = max(2 * self.zoom, 1)
            
            # Latimea disponibila pentru text (cu padding strict)
            available_text_width = rect_w - 2 * padding_x
            
            # Verifica ca avem suficient spatiu pentru text
            if available_text_width <= 2:
                return
            
            # Calculeaza numarul maxim de linii care incap
            available_height = rect_h - 2 * padding_y
            max_lines = max(1, int(available_height / scaled_line_height))
            
            # Limiteaza numarul de linii afisate
            display_lines = lines[:min(max_lines, 3)]
            
            # Calculeaza pozitia de start pentru centrarea verticala
            total_text_height = len(display_lines) * scaled_line_height
            start_y = y + (total_text_height / 2) - (scaled_line_height / 2)
            
            for idx, line in enumerate(display_lines):
                y_offset = start_y - idx * scaled_line_height
                
                # Verifica boundurile verticale
                if y_offset < bottom + padding_y or y_offset > top - padding_y - scaled_line_height/2:
                    continue
                
                # Afiseaza textul scalat
                self.display_text_scaled(line, x, y_offset, available_text_width, self.zoom)

            # Numarul de vizite sub nod - DOAR la zoom >= 1.0
            if rect_h > 15:
                node_id = id(node)
                visit_count = self.node_visit_counts.get(node_id, 0)
                if visit_count > 0:
                    glColor4f(0.6, 0.6, 0.6, text_alpha * 0.8)
                    count_text = f"({visit_count})"
                    
                    # Pozitioneaza count-ul in partea de jos a nodului
                    count_y = bottom + padding_y + 2
                    
                    # Verifica ca count-ul incape in nod
                    if count_y < top - padding_y:
                        count_width = available_text_width * 0.6
                        # Afiseaza count-ul
                        self.display_text_scaled(count_text, x, count_y, count_width, self.zoom)

    def _draw_nodes(self, node):
        """Draw all nodes cu culling imbunatatit pentru distanțe foarte reduse."""
        node_id = id(node)
        if node_id in self.node_positions:
            x, y = self.node_positions[node_id]
            
            # Apply scroll offset
            screen_x = x + self.scroll_x
            screen_y = y + self.scroll_y
            
            # Culling imbunatatit cu margini foarte reduse pentru compactitate
            node_width = self.get_node_rect_width(node)
            node_height = self.get_node_rect_height(node)
            
            # Marge pentru culling foarte reduse pentru compactitate maxima
            margin_x = max(node_width * 1.1, 20)   # Marja foarte redusa
            margin_y = max(node_height * 1.1, 20)  # Marja foarte redusa
            
            if (screen_x > -margin_x and screen_x < self.screen_width + margin_x and
                screen_y > -margin_y and screen_y < self.screen_height + margin_y):
                
                highlighted = (node == self.current_node)
                self.draw_node(node, screen_x, screen_y, highlighted)
        
        # Draw children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._draw_nodes(child)


    def zoom_at_mouse_position(self, zoom_in):
        """Zoom in/out at the current mouse position - IMPROVED boundary handling."""
        old_zoom = self.zoom
        
        # Calculate new zoom level
        if zoom_in:
            new_zoom = min(self.zoom + self.zoom_factor, self.max_zoom_in)
        else:
            new_zoom = max(self.zoom - self.zoom_factor, 0.01)
        
        if new_zoom == old_zoom:
            return  # No zoom change
        
        # Save current state
        old_scroll_x = self.scroll_x
        old_scroll_y = self.scroll_y
        
        # Update zoom and recalculate positions
        self.zoom = new_zoom
        self.calculate_node_positions()
        
        # Special handling for very low zoom levels (< 1.0)
        if old_zoom < 1.0 and new_zoom >= old_zoom:
            # When zooming from very low levels, use a more conservative approach
            
            if old_zoom < 0.5:
                # At very low zoom, the tree positioning is more sensitive
                center_x = self.screen_width / 2
                center_y = self.screen_height / 2
                
                # Calculate mouse offset from center (normalized)
                mouse_offset_x = (self.mouse_x - center_x) / self.screen_width
                mouse_offset_y = (self.mouse_y - center_y) / self.screen_height
                
                # Apply a gentle adjustment proportional to zoom change and mouse position
                zoom_change_factor = (new_zoom - old_zoom) / old_zoom
                adjustment_strength = min(zoom_change_factor * 0.3, 0.5)
                
                # Calculate gentle scroll adjustment
                adjustment_x = mouse_offset_x * self.screen_width * adjustment_strength * 0.1
                adjustment_y = mouse_offset_y * self.screen_height * adjustment_strength * 0.1
                
                self.scroll_x = old_scroll_x - adjustment_x
                self.scroll_y = old_scroll_y - adjustment_y
                
            else:
                # For zoom levels closer to 1.0, use standard calculation but with dampening
                zoom_ratio = new_zoom / old_zoom
                
                center_x = self.screen_width / 2
                center_y = self.screen_height / 2
                mouse_offset_x = self.mouse_x - center_x
                mouse_offset_y = self.mouse_y - center_y
                
                # Apply dampening factor for smoother transition
                dampening = min(old_zoom, 0.8)
                scale_adjustment_x = mouse_offset_x * (zoom_ratio - 1) * dampening
                scale_adjustment_y = mouse_offset_y * (zoom_ratio - 1) * dampening
                
                self.scroll_x = old_scroll_x * zoom_ratio - scale_adjustment_x
                self.scroll_y = old_scroll_y * zoom_ratio - scale_adjustment_y
        
        else:
            # Standard zoom handling for higher zoom levels (>= 1.0)
            zoom_ratio = new_zoom / old_zoom
            
            center_x = self.screen_width / 2
            center_y = self.screen_height / 2
            mouse_offset_x = self.mouse_x - center_x
            mouse_offset_y = self.mouse_y - center_y
            
            scale_adjustment_x = mouse_offset_x * (zoom_ratio - 1)
            scale_adjustment_y = mouse_offset_y * (zoom_ratio - 1)
            
            self.scroll_x = old_scroll_x * zoom_ratio - scale_adjustment_x
            self.scroll_y = old_scroll_y * zoom_ratio - scale_adjustment_y
        
        # Apply boundary constraints - IMPROVED with better edge case handling
        if self.node_positions:
            tree_bounds = self.get_tree_bounds_with_scroll(self.scroll_x, self.scroll_y)
            
            # Check if tree is completely outside bounds and needs aggressive correction
            min_x, max_x, min_y, max_y = tree_bounds
            margin = 50
            
            # More aggressive correction if tree is completely out of view
            if (max_x < 0 or min_x > self.screen_width or 
                max_y < 0 or min_y > self.screen_height):
                # Center the tree if it's completely out of view
                tree_center_x = (min_x + max_x) / 2
                tree_center_y = (min_y + max_y) / 2
                screen_center_x = self.screen_width / 2
                screen_center_y = self.screen_height / 2
                
                self.scroll_x += screen_center_x - tree_center_x
                self.scroll_y += screen_center_y - tree_center_y
            else:
                # Normal constraint application - apply constraints more strictly
                constrained_scroll = self.constrain_scroll_to_bounds(self.scroll_x, self.scroll_y, tree_bounds)
                
                # Force apply the constraints to prevent tree from escaping
                self.scroll_x = constrained_scroll[0]
                self.scroll_y = constrained_scroll[1]
        
        glutPostRedisplay()
    
    def get_tree_bounds_with_scroll(self, scroll_x, scroll_y):
        """Calculate the bounds of the tree with given scroll offsets."""
        if not self.node_positions:
            return (0, 0, 0, 0)
        
        # Get all node positions with scroll applied
        screen_positions = []
        for node_id, (x, y) in self.node_positions.items():
            screen_x = x + scroll_x
            screen_y = y + scroll_y
            screen_positions.append((screen_x, screen_y))
        
        # Calculate bounds
        min_x = min(pos[0] for pos in screen_positions)
        max_x = max(pos[0] for pos in screen_positions)
        min_y = min(pos[1] for pos in screen_positions)
        max_y = max(pos[1] for pos in screen_positions)
        
        return (min_x, max_x, min_y, max_y)

        
    def constrain_scroll_to_bounds(self, scroll_x, scroll_y, tree_bounds):
        """Constrain scroll values to keep tree within screen bounds - FIXED coordinate system."""
        min_x, max_x, min_y, max_y = tree_bounds
        
        # Add node size margins to bounds
        margin = 50
        
        # Constrain horizontal scrolling
        constrained_scroll_x = scroll_x
        if max_x < margin:  # Tree is too far left
            constrained_scroll_x = scroll_x + (margin - max_x)
        elif min_x > self.screen_width - margin:  # Tree is too far right
            constrained_scroll_x = scroll_x - (min_x - (self.screen_width - margin))
        
        # Constrain vertical scrolling - FIXED for OpenGL coordinate system
        constrained_scroll_y = scroll_y
        if min_y < margin:  # Tree is too far down (bottom edge)
            constrained_scroll_y = scroll_y + (margin - min_y)
        elif max_y > self.screen_height - margin:  # Tree is too far up (top edge)
            constrained_scroll_y = scroll_y - (max_y - (self.screen_height - margin))
        
        return (constrained_scroll_x, constrained_scroll_y)
    
    def motion(self, x, y):
        """Handle mouse motion with zoom-aware panning and mouse position tracking."""
        # Update mouse position for zoom calculations
        self.mouse_x = x
        self.mouse_y = self.screen_height - y  # Convert to OpenGL coordinates
        
        if self.dragging:
            dx = x - self.last_x
            dy = y - self.last_y
            
            # Scale panning speed with zoom level - slower panning when zoomed in
            pan_scale = 1.0 / self.zoom
            
            # Calculate new scroll positions
            new_scroll_x = self.scroll_x + dx * pan_scale
            new_scroll_y = self.scroll_y - dy * pan_scale  # Invert Y because OpenGL Y is bottom-up
            
            # Apply boundary constraints to keep tree visible - STRICT ENFORCEMENT
            if self.zoom < 2.0 and self.node_positions:
                # Calculate tree bounds with new scroll
                tree_bounds = self.get_tree_bounds_with_scroll(new_scroll_x, new_scroll_y)
                
                # Apply constraints strictly
                constrained_scroll = self.constrain_scroll_to_bounds(new_scroll_x, new_scroll_y, tree_bounds)
                
                self.scroll_x = constrained_scroll[0]
                self.scroll_y = constrained_scroll[1]
            else:
                self.scroll_x = new_scroll_x
                self.scroll_y = new_scroll_y
                
            self.last_x = x
            self.last_y = y
            glutPostRedisplay()

    def reshape(self, width, height):
        """Handle window reshape - FIX PENTRU DISPARIȚIA LA RESIZE."""
        self.screen_width = width
        self.screen_height = height
        
        # Set viewport
        glViewport(0, 0, width, height)
        
        # Reset projection matrix properly
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()  # IMPORTANT: Reset matricea înainte de glOrtho
        glOrtho(0, width, 0, height, -1, 1)
        
        # Switch back to modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Recalculate positions for new window size
        self.calculate_node_positions()
        glutPostRedisplay()

    def get_text_alpha(self):
        """Calculate text alpha cu tranzitii mai fine pentru zoom extins - NU afiseaza text sub zoom 1.4"""
        if self.zoom >= 1.4:
            return 1.0  # Fully visible doar la zoom >= 1.4
        else:
            return 0.0  # Complet invizibil sub zoom 1.0

    

    def get_node_rect_height(self, node):
        """Returneaza inaltimea dreptunghiului pentru un nod cu dimensiune minima foarte redusa si prevenirea suprapunerii - imbunatatit."""
        name = getattr(node, 'name', '')
        lines = name.split('\n')
        
        # Calculeaza inaltimea bazei fara zoom - parametri redusi si mai controlati
        base_line_height = 9   # REDUS: de la 10 la 9
        base_padding_y = 1.5   # REDUS: de la 2 la 1.5
        base_height = len(lines) * base_line_height + 2 * base_padding_y
        
        # Scaleaza cu zoom-ul, dar cu o dimensiune minima care previne suprapunerea
        scaled_height = base_height * self.zoom
        
        # Dimensiune minima in functie de zoom cu prevenirea suprapunerii - mai controlata
        if self.zoom >= 0.6:
            min_height = 8   # REDUS: de la 6 la 8 pentru a avea loc pentru text
        elif self.zoom >= 0.4:
            min_height = 7   # Text readable
        elif self.zoom >= 0.2:
            min_height = 6   # Text minimal
        elif self.zoom >= 0.1:
            min_height = 5   # Structural visibility
        elif self.zoom >= 0.05:
            min_height = 4   # Doar structura
        else:
            min_height = 3   # Minim absolut pentru vizibilitate
        
        # Asigura-te ca inaltimea este suficienta pentru a evita suprapunerea
        final_height = max(scaled_height, min_height)
        
        # Pentru noduri cu text lung asigura inaltime minima suplimentara
        if len(name) > 20 and self.zoom > 0.3:
            final_height = max(final_height, 12)
        elif len(name) > 15 and self.zoom > 0.2:
            final_height = max(final_height, 10)
        
        return final_height

    def get_node_rect_width(self, node):
        """Returneaza latimea dreptunghiului pentru un nod cu prevenirea suprapunerii imbunatatita si spatiu pentru text."""
        name = getattr(node, 'name', '')
        lines = name.split('\n')
        
        # Calculeaza latimea bazei fara zoom - parametri ajustati pentru text
        base_padding_x = 3     # Padding suficient pentru text
        base_char_width = 5    # Latime caracter mai realista
        max_text_width = max(len(line) for line in lines) * base_char_width
        base_width = max(self.node_width * 0.6, max_text_width + 2 * base_padding_x)  # 60% din node_width
        
        # Scaleaza cu zoom-ul
        scaled_width = base_width * self.zoom
        
        # Dimensiune minima in functie de zoom cu spatiu pentru text
        if self.zoom >= 0.6:
            min_width = 15   # Suficient pentru text complet
        elif self.zoom >= 0.4:
            min_width = 12   # Text prescurtat
        elif self.zoom >= 0.2:
            min_width = 10   # Text minimal
        elif self.zoom >= 0.1:
            min_width = 8    # Initiale
        else:
            min_width = 6    # Structural only
        
        # Asigura latimea minima pentru prevenirea suprapunerii
        final_width = max(scaled_width, min_width)
        
        # Pentru noduri cu text foarte lung asigura latime suplimentara
        if len(name) > 25 and self.zoom > 0.4:
            final_width = max(final_width, len(name) * 2 + 10)
        elif len(name) > 20 and self.zoom > 0.3:
            final_width = max(final_width, len(name) * 1.5 + 8)
        
        return final_width


    def _calculate_subtree_widths(self, node, widths):
        """Calculeaza latimile subtree-urilor cu distante foarte reduse si prevenirea suprapunerii."""
        # Latimea nodului curent
        node_req_width = self.get_node_rect_width(node)
        
        if not hasattr(node, 'children') or not node.children:
            widths[id(node)] = node_req_width
            return node_req_width

        # Internal node - sum of children widths plus spatii foarte reduse
        total_width = 0
        for child in node.children:
            child_width = self._calculate_subtree_widths(child, widths)
            total_width += child_width

        # Distanta intre frati FOARTE REDUSA cu prevenirea suprapunerii
        if len(node.children) > 1:
            # Foloseste distanta adaptiva foarte redusa
            adaptive_distance = self.get_adaptive_spacing()
            
            # Asigura-te ca distanta nu este mai mica decat minimul necesar pentru zoom
            min_spacing_for_zoom = max(1.5, 3 * self.zoom)  # Scaling mai agresiv cu zoom-ul
            final_spacing = max(adaptive_distance, min_spacing_for_zoom)
            
            total_width += (len(node.children) - 1) * final_spacing

        # Latimea finala cu marja minima pentru compactitate maxima
        final_width = max(total_width, node_req_width * 1.03)  # Marja de doar 3%
        
        widths[id(node)] = final_width
        return final_width

    

    

    

    

    def get_zoom_level_description(self):
        """Get a description cu niveluri extinse de zoom pana la 3.0."""
        if self.zoom >= 3.0:
            return "Maximum zoom (3.0x)"
        elif self.zoom >= 2.5:
            return "Very close zoom"
        elif self.zoom >= 2.0:
            return "Close zoom"
        elif self.zoom >= 1.5:
            return "Medium close zoom"
        elif self.zoom >= 1.0:
            return "Normal view"
        elif self.zoom >= 0.6:
            return "Medium overview"
        elif self.zoom >= 0.3:
            return "Wide overview"
        elif self.zoom >= 0.15:
            return "Far overview (minimal text)"
        elif self.zoom >= 0.05:
            return "Very far overview (initials only)"
        else:
            return "Extreme overview (structure only)"

    def is_node_visible_at_zoom(self, node):
        """Determine if a node should be rendered at the current zoom level."""
        # At very low zoom levels, we might want to skip rendering some nodes
        # to improve performance, but for now, render all nodes
        return True

    def get_adaptive_font_size(self):
        """Get font size that adapts to zoom level - imbunatatit."""
        # Calculeaza o dimensiune efectiva de font bazata pe zoom
        base_size = 12
        scaled_size = int(base_size * min(max(self.zoom, 0.3), 2.0))
        return max(scaled_size, 6)  # Minimum 6px

    def update_view_bounds(self):
        """Update the visible bounds for efficient culling."""
        # Calculate what's actually visible on screen considering zoom and scroll
        visible_left = -self.scroll_x / self.zoom
        visible_right = (self.screen_width - self.scroll_x) / self.zoom
        visible_bottom = -self.scroll_y / self.zoom  
        visible_top = (self.screen_height - self.scroll_y) / self.zoom
        
        return {
            'left': visible_left,
            'right': visible_right, 
            'bottom': visible_bottom,
            'top': visible_top
        }

    def optimize_rendering_for_zoom(self):
        """Apply zoom-specific optimizations."""
        if self.zoom < 0.3:
            # At very low zoom, disable some expensive rendering features
            glDisable(GL_LINE_SMOOTH)
            glDisable(GL_POINT_SMOOTH)
        else:
            # Enable anti-aliasing for better quality at higher zoom
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def draw_tree(self):
        """Draw the entire tree."""
        if not self.root:
            return
        
        # Draw connections first (so they appear behind nodes)
        self._draw_connections(self.root)
        
        # Then draw nodes
        self._draw_nodes(self.root)


    def draw_zoom_indicator(self):
        """Draw a zoom level indicator in the corner cu range extins pana la 3.0."""
        if self.zoom < 1.0:
            return  # Nu afisa zoom indicator sub zoom 1.0
            
        text_alpha = max(0.3, self.get_text_alpha())
        glColor4f(0.7, 0.7, 1.0, text_alpha)
        
        # Position in bottom-right corner
        zoom_text = f"Zoom: {self.zoom:.1f}x"
        zoom_desc = self.get_zoom_level_description()
        
        x = self.screen_width - 150
        y = 30
        
        self.display_text(zoom_text, x, y)
        self.display_text(zoom_desc, x, y - 15)
        
        # Draw a simple zoom scale bar
        bar_width = 100
        bar_height = 8
        bar_x = x
        bar_y = y - 35
        
        # Background bar
        glColor4f(0.3, 0.3, 0.3, text_alpha)
        glBegin(GL_QUADS)
        glVertex2f(bar_x, bar_y)
        glVertex2f(bar_x + bar_width, bar_y)
        glVertex2f(bar_x + bar_width, bar_y + bar_height)
        glVertex2f(bar_x, bar_y + bar_height)
        glEnd()
        
        # Zoom level indicator cu range extins la 3.0
        max_zoom = 3.0  # Actualizat la 3.0
        zoom_progress = (self.zoom - self.max_zoom_out) / (max_zoom - self.max_zoom_out)
        zoom_progress = max(0, min(1, zoom_progress))
        indicator_x = bar_x + zoom_progress * bar_width
        
        glColor4f(0.0, 0.8, 0.0, text_alpha)
        glBegin(GL_QUADS)
        glVertex2f(bar_x, bar_y)
        glVertex2f(indicator_x, bar_y)  
        glVertex2f(indicator_x, bar_y + bar_height)
        glVertex2f(bar_x, bar_y + bar_height)
        glEnd()

    

    def get_edge_color(self, parent_node, child_node, base_color):
        """Get edge color considering visit state and timer"""
        edge_key = (id(parent_node), id(child_node))
        visit_count = self.edge_visit_counts.get(edge_key, 0)
        
        # If visit count is 0 (not visited or timer expired) or > 1 (already highlighted)
        if visit_count == 0:
            return base_color
        
        # If timer is active
        timer_value = self.edge_timers.get(edge_key, self.global_edge_timer)
        fade_factor = timer_value / self.global_edge_timer
        
        # Interpolate between highlight color and white
        r = base_color[0] + (1.0 - base_color[0]) * fade_factor
        g = base_color[1] + (1.0 - base_color[1]) * fade_factor
        b = base_color[2] + (1.0 - base_color[2]) * fade_factor
        
        return (r, g, b)

    def _find_path_for_data(self, node, data_values, column_names):
        """Find the path through the tree for given data values."""
        path = [node]
        current = node
        
        while hasattr(current, 'children') and current.children:
            name = getattr(current, 'name', '')
            
            # Parse the decision condition
            if '<=' in name:
                # Extract feature name and threshold
                parts = name.split('<=')
                if len(parts) == 2:
                    feature_name = parts[0].strip()
                    try:
                        threshold = float(parts[1].strip())
                        
                        # Find the feature in our data
                        if feature_name in column_names:
                            feature_index = column_names.index(feature_name)
                            if feature_index < len(data_values):
                                feature_value = float(data_values[feature_index])
                                
                                # Choose child based on condition
                                if feature_value <= threshold:
                                    # Go left (first child)
                                    if len(current.children) > 0:
                                        current = current.children[0]
                                        path.append(current)
                                else:
                                    # Go right (second child)
                                    if len(current.children) > 1:
                                        current = current.children[1]
                                        path.append(current)
                                    elif len(current.children) > 0:
                                        current = current.children[0]
                                        path.append(current)
                                continue
                    except ValueError:
                        pass
            
            # If we couldn't parse the condition just take the first child
            current = current.children[0]
            path.append(current)
            break
        
        return path

    def init_gl(self):
        """Initialize OpenGL settings."""
        glClearColor(*self.bg_color)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        # Set up the font
        try:
            self.font = GLUT_BITMAP_HELVETICA_12
        except:
            try:
                self.font = GLUT_BITMAP_9_BY_15
            except:
                self.font = None

    def run(self, window_title="Tree Visualization"):
        """Start and run the visualization with enhanced controls."""
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
        glutPassiveMotionFunc(self.passive_mouse_motion)
        glutKeyboardFunc(self.keyboard)  # Add keyboard support
        glutReshapeFunc(self.reshape)    # Add window reshape support
        glutIdleFunc(self.idle)          # Add idle function for auto-redraw
        
        # Initialize OpenGL settings
        self.init_gl()
        
        # Print controls to console
        print("=== Tree Visualization Controls ===")
        print("Mouse:")
        print("  - Left Click + Drag: Pan view")
        print("  - Mouse Wheel: Zoom in/out")
        print("Keyboard:")
        print("  - R: Reset view to default")
        print("  - +/=: Zoom in")
        print("  - -/_: Zoom out") 
        print("  - ESC: Exit")
        print("Features:")
        print("  - Text fades out when zooming out")
        print("  - Connection lines get thicker when zoomed out")
        print("  - Adaptive text abbreviation at very low zoom")
        print("=====================================")
        
        # Enter the main loop
        glutMainLoop()


    

def highlight_path_for_data_line(data_values, column_names):
    """
    Standalone function to highlight the path in the decision tree for given data values.
    
    Args:
        data_values: List of data values 
        column_names: List of column names in order
    """
    global _global_visualizer
    
    if _global_visualizer is None:
        print("Error: No tree visualization is currently running!")
        print("Please start the tree visualization first.")
        return
    
    try:
        # Use the global visualizer instance to highlight the path
        _global_visualizer.highlight_path_for_data(data_values, column_names)
        print("Path highlighted successfully!")
        
    except Exception as e:
        print(f"Error highlighting path: {e}")


# Global visualizer instance for external control
_global_visualizer = None

def visualize_binary_tree(root_node, window_title="Tree Visualization"):
    global _global_visualizer
    _global_visualizer = TreeVisualizer(screen_width=1400, screen_height=800)
    _global_visualizer.set_tree(root_node)
    _global_visualizer.run(window_title)


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