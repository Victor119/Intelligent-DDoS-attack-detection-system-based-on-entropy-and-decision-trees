import sys
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import threading
import random

class TreeVisualizer:
    
    def __init__(self, screen_width=1200, screen_height=700, bg_color=(0.2, 0.2, 0.2, 1.0)):
        """Initialize the TreeVisualizer cu setări îmbunătățite pentru distanțe foarte reduse.""" 
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.bg_color = bg_color
        self.root = None
        
        # Node size and spacing parameters - distanțe foarte reduse pentru compactitate maximă
        self.node_radius = 18          # REDUS: de la 20 la 18
        self.level_height = 60         # REDUS SEMNIFICATIV: de la 80 la 60
        self.min_node_distance = 4     # REDUS: de la 6 la 4
        self.node_width = 90           # REDUS: de la 100 la 90
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
        self.text_color = (0.89, 0.33, 0.05)
        self.line_color = (0.0, 0.7, 0.0)
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


    def set_tree(self, root_node):
        """Set the root node of the tree to visualize."""
        self.root = root_node
        if root_node:
            self.calculate_node_positions()
            # Initialize node colors and visit counts
            self._initialize_node_properties(root_node)

    def _initialize_node_properties(self, node):
        """Initialize node properties like colors and visit counts."""
        node_id = id(node)
        
        # Initialize visit count
        if node_id not in self.node_visit_counts:
            self.node_visit_counts[node_id] = 0
        
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

    def get_adaptive_spacing(self):
        """Calculate adaptive spacing între noduri cu prevenirea suprapunerii îmbunătățită și reducere la zoom out."""
        # Distanța de bază foarte redusă
        base_spacing = 4  # REDUS: de la 6 la 4
        
        # Calculează dimensiunea medie a nodurilor pentru a preveni suprapunerea
        if self.root and self.node_positions:
            # Estimează dimensiunea nodului la zoom-ul curent
            sample_node_width = self.get_node_rect_width(self.root) * self.zoom
            sample_node_height = self.get_node_rect_height(self.root) * self.zoom
            
            # Distanța minimă necesară pentru a evita suprapunerea
            min_required_spacing = max(sample_node_width * 0.05, sample_node_height * 0.05, 2)  # REDUS
        else:
            min_required_spacing = 2  # REDUS de la 3
        
        # Adaptează spacing-ul în funcție de zoom cu prevenirea suprapunerii - mai agresiv la zoom out
        if self.zoom >= 1.0:
            spacing = max(base_spacing, min_required_spacing)
        elif self.zoom >= 0.8:
            spacing = max(base_spacing * 1.1, min_required_spacing)  # 4.4 pixels - REDUS
        elif self.zoom >= 0.6:
            spacing = max(base_spacing * 1.2, min_required_spacing)  # 4.8 pixels - REDUS
        elif self.zoom >= 0.4:
            spacing = max(base_spacing * 1.3, min_required_spacing)  # 5.2 pixels - REDUS
        elif self.zoom >= 0.3:
            spacing = max(base_spacing * 1.4, min_required_spacing)  # 5.6 pixels - REDUS
        elif self.zoom >= 0.2:
            spacing = max(base_spacing * 1.5, min_required_spacing)  # 6 pixels - REDUS
        elif self.zoom >= 0.15:
            spacing = max(base_spacing * 1.6, min_required_spacing)  # 6.4 pixels - REDUS
        elif self.zoom >= 0.08:
            spacing = max(base_spacing * 1.8, min_required_spacing)  # 7.2 pixels - REDUS
        else:
            # La zoom foarte mic, spacing minim pentru compactitate extremă
            spacing = max(base_spacing * 2.0, min_required_spacing)  # 8 pixels - FOARTE REDUS
        
        return spacing

    def get_adaptive_level_height(self):
        """Calculează înălțimea adaptivă între niveluri cu prevenirea suprapunerii și reducere mai agresivă la zoom out."""
        # Înălțimea de bază foarte redusă
        base_level_height = 60  # REDUS: de la 80 la 60
        
        # Calculează înălțimea necesară pentru a evita suprapunerea nodurilor
        if self.root:
            sample_node_height = self.get_node_rect_height(self.root)
            min_required_height = sample_node_height * 1.2  # Redus de la 1.4 la 1.2 pentru compactitate
        else:
            min_required_height = 30  # Redus de la 40
        
        # La zoom mare, păstrează distanța redusă dar sigură
        if self.zoom >= 1.0:
            return max(base_level_height, min_required_height)
        elif self.zoom >= 0.8:
            return max(base_level_height * 0.9, min_required_height)   # 54 pixels - REDUS
        elif self.zoom >= 0.6:
            return max(base_level_height * 0.8, min_required_height)   # 48 pixels - REDUS
        elif self.zoom >= 0.4:
            return max(base_level_height * 0.7, min_required_height)   # 42 pixels - REDUS
        elif self.zoom >= 0.3:
            return max(base_level_height * 0.6, min_required_height)   # 36 pixels - REDUS SEMNIFICATIV
        elif self.zoom >= 0.2:
            return max(base_level_height * 0.5, min_required_height)   # 30 pixels - FOARTE REDUS
        elif self.zoom >= 0.1:
            return max(base_level_height * 0.4, min_required_height)   # 24 pixels - EXTREM DE REDUS
        elif self.zoom >= 0.05:
            return max(base_level_height * 0.35, min_required_height)  # 21 pixels - ULTRA REDUS
        else:
            # La zoom foarte mic, distanță minimă pentru vizibilitate
            return max(base_level_height * 0.3, min_required_height)   # 18 pixels - MINIMAL


    def get_text_alpha(self):
        """Calculate text alpha cu tranziții mai fine pentru zoom extins - NU afișează text sub zoom 1.00."""
        if self.zoom >= 1.0:
            return 1.0  # Fully visible doar la zoom >= 1.0
        else:
            return 0.0  # Complet invizibil sub zoom 1.0

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
        """Calculate positions for all nodes cu distanțe adaptive și înălțimi foarte reduse la zoom out."""
        if not self.root:
            return
        
        self.node_positions = {}
        
        # First pass: calculate the width needed for each subtree cu distanțe adaptive
        subtree_widths = {}
        self._calculate_subtree_widths(self.root, subtree_widths)
        
        # Second pass: assign positions based on calculated widths
        root_width = subtree_widths[id(self.root)]
        start_x = 0
        start_y = self.screen_height - 100
        
        # Înălțimea între niveluri FOARTE ADAPTIVĂ - se reduce semnificativ la zoom out
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
        """Assign actual positions to nodes cu spacing îmbunătățit și prevenirea suprapunerii."""
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
        
        # Calculate positions for children cu spacing îmbunătățit
        child_y = y - level_height
        current_x = x
        adaptive_distance = self.get_adaptive_spacing()
        
        # Verifică dacă copiii se suprapun și ajustează dacă e necesar
        total_children_width = sum(subtree_widths[id(child)] for child in children)
        total_spacing_needed = (num_children - 1) * adaptive_distance
        total_required_width = total_children_width + total_spacing_needed
        
        # Dacă lățimea disponibilă este mai mică decât cea necesară, reduce spacing-ul inteligent
        if total_required_width > available_width and num_children > 1:
            # Calculează spacing-ul maxim posibil fără suprapunere
            max_possible_spacing = (available_width - total_children_width) / (num_children - 1)
            # Asigură un minimum absolut pentru prevenirea suprapunerii complete
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
        """Get the color for a node based on its type and visit count."""
        node_id = id(node)
        base_color_key = self.node_base_colors.get(node_id, 'blue')
        visit_count = self.node_visit_counts.get(node_id, 0)
        
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
        """Adaptează textul în funcție de nivelul de zoom și lățimea disponibilă - fără puncte."""
        if not text:
            return ""
        
        # Estimează lățimea unui caracter la zoom-ul curent (mai precis)
        char_width = max(4 * zoom_level, 1.5)
        max_chars = int(max_width_pixels / char_width)
        
        if max_chars <= 0:
            return ""
        
        # Scalare text în funcție de zoom - fără puncte
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
                # Încearcă să păstreze partea importantă
                if "Class:" in text:
                    short_text = text.replace("Class:", "C:")
                    if len(short_text) <= max_chars:
                        return short_text
                    else:
                        return short_text[:max_chars]
                elif "<=" in text:
                    # Pentru condiții, păstrează partea principală
                    feature_part = text.split("<=")[0].strip()
                    if len(feature_part) <= max_chars:
                        return feature_part
                    else:
                        return feature_part[:max_chars]
                else:
                    return text[:max_chars]
        elif zoom_level >= 0.1:
            # Pentru zoom foarte mic, doar cuvinte cheie
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
            # Pentru zoom extrem de mic, doar inițiale
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
        """Display text scalat cu zoom-ul și limitare de lățime fără puncte și fără distanțare la zoom-in."""
        if not text or zoom_level < 0.02:
            return
        
        # Adaptează textul să încapă în lățimea disponibilă
        adapted_text = self.get_adaptive_text(text, max_width, zoom_level)
        if not adapted_text:
            return
        
        # Calculează poziția exactă pentru a centra textul - folosește lățimea font-ului standard
        estimated_text_width = len(adapted_text) * 6  # Lățime fixă standard pentru caracter
        centered_x = x - estimated_text_width / 2
        
        glRasterPos2f(centered_x, y)
        
        if self.font is None:
            return
        
        try:
            # Pentru zoom foarte mic, simulează font mai mic prin sărirea caracterelor
            if zoom_level < 0.08:
                # Afișează doar fiecare al 2-lea sau 3-lea caracter pentru efect de "font mic"
                step = max(1, int(0.15 / max(zoom_level, 0.01)))
                displayed_text = adapted_text[::step]
            elif zoom_level < 0.15:
                # Afișează majoritatea caracterelor
                displayed_text = adapted_text
            else:
                displayed_text = adapted_text
            
            # Afișează caracterele FĂRĂ spacing custom - lasă font-ul să gestioneze spacing-ul
            for char in displayed_text:
                glutBitmapCharacter(self.font, ord(char))
                
        except:
            pass

    def draw_node(self, node, x, y, highlighted=False):
        """Draw a tree node cu text scalat - NU afișează text sub zoom 1.00."""
        name = getattr(node, 'name', '')
        in_path = self.is_node_in_highlighted_path(node)
        text_alpha = self.get_text_alpha()

        # Alege culoarea
        if highlighted:
            glColor3f(*self.highlight_color)
        else:
            node_color = self.get_node_color(node)
            glColor3f(*node_color)

        # Pregăteşte liniile de text
        lines = []
        if "<=" in name:    
            lines = [name]
        elif name.startswith("Class:"):
            lines = [name]
        else:
            lines = [name]

        # Calculează dimensiunea dreptunghiului
        rect_w = self.get_node_rect_width(node)
        rect_h = self.get_node_rect_height(node)

        # Colţurile dreptunghiului
        left   = x - rect_w/2
        right  = x + rect_w/2
        top    = y + rect_h/2
        bottom = y - rect_h/2

        # Desenează dreptunghiul
        glBegin(GL_POLYGON)
        glVertex2f(left,  top)
        glVertex2f(right, top)
        glVertex2f(right, bottom)
        glVertex2f(left,  bottom)
        glEnd()

        # Contur cu grosime foarte redusă pentru compactitate
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

        # Textul centrat - DOAR la zoom >= 1.0
        if self.zoom >= 1.0 and text_alpha > 0.008 and rect_w > 6 and rect_h > 6:
            # Set text color with alpha
            text_color_with_alpha = (*self.text_color, text_alpha)
            glColor4f(*text_color_with_alpha)
            
            # Calculează dimensiunea scalată a textului cu compactitate maximă
            scaled_line_height = max(8 * self.zoom, 3)
            padding_y = max(1 * self.zoom, 0.3)
            padding_x = max(2 * self.zoom, 1)
            
            # Lățimea disponibilă pentru text (cu padding strict)
            available_text_width = rect_w - 2 * padding_x
            
            # Verifică că avem suficient spațiu pentru text
            if available_text_width <= 2:
                return
            
            # Calculează numărul maxim de linii care încap
            available_height = rect_h - 2 * padding_y
            max_lines = max(1, int(available_height / scaled_line_height))
            
            # Limitează numărul de linii afișate
            display_lines = lines[:min(max_lines, 3)]
            
            # Calculează poziția de start pentru centrarea verticală
            total_text_height = len(display_lines) * scaled_line_height
            start_y = y + (total_text_height / 2) - (scaled_line_height / 2)
            
            for idx, line in enumerate(display_lines):
                y_offset = start_y - idx * scaled_line_height
                
                # Verifică boundurile verticale
                if y_offset < bottom + padding_y or y_offset > top - padding_y - scaled_line_height/2:
                    continue
                
                # Afișează textul scalat
                self.display_text_scaled(line, x, y_offset, available_text_width, self.zoom)

            # Numărul de vizite sub nod - DOAR la zoom >= 1.0
            if rect_h > 15:
                node_id = id(node)
                visit_count = self.node_visit_counts.get(node_id, 0)
                if visit_count > 0:
                    glColor4f(0.6, 0.6, 0.6, text_alpha * 0.8)
                    count_text = f"({visit_count})"
                    
                    # Poziționează count-ul în partea de jos a nodului
                    count_y = bottom + padding_y + 2
                    
                    # Verifică că count-ul încape în nod
                    if count_y < top - padding_y:
                        count_width = available_text_width * 0.6
                        # Afișează count-ul
                        self.display_text_scaled(count_text, x, count_y, count_width, self.zoom)

    def draw_line(self, x1, y1, x2, y2, is_path_line=False):
        """Draw a line between two points."""
        line_width_multiplier = self.get_line_width_multiplier()
        
        if is_path_line:
            glColor3f(*self.path_line_color)
            glLineWidth(4.0 * line_width_multiplier)
        else:
            glColor3f(*self.line_color)
            glLineWidth(2.0 * line_width_multiplier)
        
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()
    
    def _is_connection_in_path(self, parent_node, child_node):
        """Check if a connection between parent and child is in the highlighted path."""
        with self.path_lock:
            parent_id = id(parent_node)
            child_id = id(child_node)
            return parent_id in self.highlighted_paths and child_id in self.highlighted_paths

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
        
        # Scale node radius with zoom
        scaled_node_radius = self.node_radius * self.zoom
        
        for child in node.children:
            child_id = id(child)
            if child_id in self.node_positions:
                child_x, child_y = self.node_positions[child_id]
                child_x += self.scroll_x
                child_y += self.scroll_y
                
                # Check if this connection is in the highlighted path
                is_path_connection = self._is_connection_in_path(node, child)
                
                # Draw line from parent to child
                self.draw_line(parent_x, parent_y - scaled_node_radius,
                            child_x, child_y + scaled_node_radius,
                            is_path_connection)
                
                # Recursively draw child connections
                self._draw_connections(child)

    def mouse(self, button, state, x, y):
        """Handle mouse input cu zoom extins."""
        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                self.dragging = True
                self.last_x = x
                self.last_y = y
            else:
                self.dragging = False
        elif button == 3:  # Mouse wheel up
            old_zoom = self.zoom
            self.zoom = min(self.zoom + self.zoom_factor, self.max_zoom_in)
            if self.zoom != old_zoom:
                self.calculate_node_positions()
                glutPostRedisplay()
        elif button == 4:  # Mouse wheel down
            old_zoom = self.zoom
            # Permite zoom out mult mai mic
            self.zoom = max(self.zoom - self.zoom_factor, 0.01)  # Schimbat de la 0.2 la 0.01
            if self.zoom != old_zoom:
                self.calculate_node_positions()
                glutPostRedisplay()

    
    def get_text_alpha(self):
        """Calculate text alpha cu tranziții mai fine pentru zoom extins - NU afișează text sub zoom 1.00."""
        if self.zoom >= 1.0:
            return 1.0  # Fully visible doar la zoom >= 1.0
        else:
            return 0.0  # Complet invizibil sub zoom 1.0

    def draw_node(self, node, x, y, highlighted=False):
        """Draw a tree node cu text scalat - NU afișează text sub zoom 1.00."""
        name = getattr(node, 'name', '')
        in_path = self.is_node_in_highlighted_path(node)
        text_alpha = self.get_text_alpha()

        # Alege culoarea
        if highlighted:
            glColor3f(*self.highlight_color)
        else:
            node_color = self.get_node_color(node)
            glColor3f(*node_color)

        # Pregăteşte liniile de text
        lines = []
        if "<=" in name:    
            lines = [name]
        elif name.startswith("Class:"):
            lines = [name]
        else:
            lines = [name]

        # Calculează dimensiunea dreptunghiului
        rect_w = self.get_node_rect_width(node)
        rect_h = self.get_node_rect_height(node)

        # Colţurile dreptunghiului
        left   = x - rect_w/2
        right  = x + rect_w/2
        top    = y + rect_h/2
        bottom = y - rect_h/2

        # Desenează dreptunghiul
        glBegin(GL_POLYGON)
        glVertex2f(left,  top)
        glVertex2f(right, top)
        glVertex2f(right, bottom)
        glVertex2f(left,  bottom)
        glEnd()

        # Contur cu grosime foarte redusă pentru compactitate
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

        # Textul centrat - DOAR la zoom >= 1.0
        if self.zoom >= 1.0 and text_alpha > 0.008 and rect_w > 6 and rect_h > 6:
            # Set text color with alpha
            text_color_with_alpha = (*self.text_color, text_alpha)
            glColor4f(*text_color_with_alpha)
            
            # Calculează dimensiunea scalată a textului cu compactitate maximă
            scaled_line_height = max(8 * self.zoom, 3)
            padding_y = max(1 * self.zoom, 0.3)
            padding_x = max(2 * self.zoom, 1)
            
            # Lățimea disponibilă pentru text (cu padding strict)
            available_text_width = rect_w - 2 * padding_x
            
            # Verifică că avem suficient spațiu pentru text
            if available_text_width <= 2:
                return
            
            # Calculează numărul maxim de linii care încap
            available_height = rect_h - 2 * padding_y
            max_lines = max(1, int(available_height / scaled_line_height))
            
            # Limitează numărul de linii afișate
            display_lines = lines[:min(max_lines, 3)]
            
            # Calculează poziția de start pentru centrarea verticală
            total_text_height = len(display_lines) * scaled_line_height
            start_y = y + (total_text_height / 2) - (scaled_line_height / 2)
            
            for idx, line in enumerate(display_lines):
                y_offset = start_y - idx * scaled_line_height
                
                # Verifică boundurile verticale
                if y_offset < bottom + padding_y or y_offset > top - padding_y - scaled_line_height/2:
                    continue
                
                # Afișează textul scalat
                self.display_text_scaled(line, x, y_offset, available_text_width, self.zoom)

            # Numărul de vizite sub nod - DOAR la zoom >= 1.0
            if rect_h > 15:
                node_id = id(node)
                visit_count = self.node_visit_counts.get(node_id, 0)
                if visit_count > 0:
                    glColor4f(0.6, 0.6, 0.6, text_alpha * 0.8)
                    count_text = f"({visit_count})"
                    
                    # Poziționează count-ul în partea de jos a nodului
                    count_y = bottom + padding_y + 2
                    
                    # Verifică că count-ul încape în nod
                    if count_y < top - padding_y:
                        count_width = available_text_width * 0.6
                        # Afișează count-ul
                        self.display_text_scaled(count_text, x, count_y, count_width, self.zoom)

    def draw_help_text(self):
        """Draw help text for navigation - DOAR la zoom >= 1.0."""
        if self.zoom < 1.0:
            return  # Nu afișa help text sub zoom 1.0
            
        text_alpha = self.get_text_alpha()
        if text_alpha > 0.01:  # Only draw help text if visible
            glColor4f(1.0, 1.0, 1.0, text_alpha)
            help_text = [
                "Navigation Controls:",
                "- Mouse Drag: Pan view",
                "- Mouse Wheel: Zoom in/out",
                f"- Current Zoom: {self.zoom:.2f}",
                "",
                "Node Coloring:",
                "- Blue/Yellow/Purple: Random assignment",
                "- Light to Dark: Visit frequency",
                "- Numbers in (): Visit count",
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

    def _draw_nodes(self, node):
        """Draw all nodes cu culling îmbunătățit pentru distanțe foarte reduse."""
        node_id = id(node)
        if node_id in self.node_positions:
            x, y = self.node_positions[node_id]
            
            # Apply scroll offset
            screen_x = x + self.scroll_x
            screen_y = y + self.scroll_y
            
            # Culling îmbunătățit cu margini foarte reduse pentru compactitate
            node_width = self.get_node_rect_width(node)
            node_height = self.get_node_rect_height(node)
            
            # Marge pentru culling foarte reduse pentru compactitate maximă
            margin_x = max(node_width * 1.1, 20)   # Marjă foarte redusă
            margin_y = max(node_height * 1.1, 20)  # Marjă foarte redusă
            
            if (screen_x > -margin_x and screen_x < self.screen_width + margin_x and
                screen_y > -margin_y and screen_y < self.screen_height + margin_y):
                
                highlighted = (node == self.current_node)
                self.draw_node(node, screen_x, screen_y, highlighted)
        
        # Draw children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._draw_nodes(child)

    def get_node_rect_height(self, node):
        """Returnează înălțimea dreptunghiului pentru un nod, cu dimensiune minimă foarte redusă și prevenirea suprapunerii - îmbunătățit."""
        name = getattr(node, 'name', '')
        lines = name.split('\n')
        
        # Calculează înălțimea bazei fără zoom - parametri reduși și mai controlați
        base_line_height = 9   # REDUS: de la 10 la 9
        base_padding_y = 1.5   # REDUS: de la 2 la 1.5
        base_height = len(lines) * base_line_height + 2 * base_padding_y
        
        # Scalează cu zoom-ul, dar cu o dimensiune minimă care previne suprapunerea
        scaled_height = base_height * self.zoom
        
        # Dimensiune minimă în funcție de zoom cu prevenirea suprapunerii - mai controlată
        if self.zoom >= 0.6:
            min_height = 8   # REDUS: de la 6 la 8 pentru a avea loc pentru text
        elif self.zoom >= 0.4:
            min_height = 7   # Text readable
        elif self.zoom >= 0.2:
            min_height = 6   # Text minimal
        elif self.zoom >= 0.1:
            min_height = 5   # Structural visibility
        elif self.zoom >= 0.05:
            min_height = 4   # Doar structură
        else:
            min_height = 3   # Minim absolut pentru vizibilitate
        
        # Asigură-te că înălțimea este suficientă pentru a evita suprapunerea
        final_height = max(scaled_height, min_height)
        
        # Pentru noduri cu text lung, asigură înălțime minimă suplimentară
        if len(name) > 20 and self.zoom > 0.3:
            final_height = max(final_height, 12)
        elif len(name) > 15 and self.zoom > 0.2:
            final_height = max(final_height, 10)
        
        return final_height

    def get_node_rect_width(self, node):
        """Returnează lățimea dreptunghiului pentru un nod cu prevenirea suprapunerii îmbunătățită și spațiu pentru text."""
        name = getattr(node, 'name', '')
        lines = name.split('\n')
        
        # Calculează lățimea bazei fără zoom - parametri ajustați pentru text
        base_padding_x = 3     # Padding suficient pentru text
        base_char_width = 5    # Lățime caracter mai realistă
        max_text_width = max(len(line) for line in lines) * base_char_width
        base_width = max(self.node_width * 0.6, max_text_width + 2 * base_padding_x)  # 60% din node_width
        
        # Scalează cu zoom-ul
        scaled_width = base_width * self.zoom
        
        # Dimensiune minimă în funcție de zoom cu spațiu pentru text
        if self.zoom >= 0.6:
            min_width = 15   # Suficient pentru text complet
        elif self.zoom >= 0.4:
            min_width = 12   # Text prescurtat
        elif self.zoom >= 0.2:
            min_width = 10   # Text minimal
        elif self.zoom >= 0.1:
            min_width = 8    # Inițiale
        else:
            min_width = 6    # Structural only
        
        # Asigură lățimea minimă pentru prevenirea suprapunerii
        final_width = max(scaled_width, min_width)
        
        # Pentru noduri cu text foarte lung, asigură lățime suplimentară
        if len(name) > 25 and self.zoom > 0.4:
            final_width = max(final_width, len(name) * 2 + 10)
        elif len(name) > 20 and self.zoom > 0.3:
            final_width = max(final_width, len(name) * 1.5 + 8)
        
        return final_width


    def _calculate_subtree_widths(self, node, widths):
        """Calculează lățimile subtree-urilor cu distanțe foarte reduse și prevenirea suprapunerii."""
        # Lățimea nodului curent
        node_req_width = self.get_node_rect_width(node)
        
        if not hasattr(node, 'children') or not node.children:
            widths[id(node)] = node_req_width
            return node_req_width

        # Internal node - sum of children widths plus spații foarte reduse
        total_width = 0
        for child in node.children:
            child_width = self._calculate_subtree_widths(child, widths)
            total_width += child_width

        # Distanța între frați FOARTE REDUSĂ cu prevenirea suprapunerii
        if len(node.children) > 1:
            # Folosește distanța adaptivă foarte redusă
            adaptive_distance = self.get_adaptive_spacing()
            
            # Asigură-te că distanța nu este mai mică decât minimul necesar pentru zoom
            min_spacing_for_zoom = max(1.5, 3 * self.zoom)  # Scaling mai agresiv cu zoom-ul
            final_spacing = max(adaptive_distance, min_spacing_for_zoom)
            
            total_width += (len(node.children) - 1) * final_spacing

        # Lățimea finală cu marjă minimă pentru compactitate maximă
        final_width = max(total_width, node_req_width * 1.03)  # Marjă de doar 3%
        
        widths[id(node)] = final_width
        return final_width

    def display_text(self, text, x, y):
        """Display text at the given position fără prescurtare cu puncte și fără distanțare la zoom-in."""
        scaled_x = x
        scaled_y = y
        
        glRasterPos2f(scaled_x, scaled_y)
        
        if self.font is None:
            return
            
        try:
            # Pentru textul general (help, zoom indicator), folosește adaptare fără puncte
            if self.zoom < 0.3:
                # Prescurtează textul pentru zoom mic fără puncte
                max_len = max(5, int(25 * self.zoom / 0.3))
                display_text = text[:max_len] if len(text) > max_len else text
            else:
                display_text = text
            
            # Pentru zoom foarte mic, prescurtare mai agresivă
            if self.zoom < 0.15:
                max_len = max(3, int(10 * self.zoom / 0.15))
                display_text = display_text[:max_len] if len(display_text) > max_len else display_text
            
            # Simulează font mai mic prin caractere mai rare la zoom mic
            if self.zoom < 0.1:
                # Afișează doar fiecare al 2-lea caracter
                display_text = display_text[::2]
            
            # Afișează textul FĂRĂ spacing manual - lasă font-ul să gestioneze spacing-ul
            for char in display_text:
                glutBitmapCharacter(self.font, ord(char))
        except:
            pass

    def motion(self, x, y):
        """Handle mouse motion with zoom-aware panning."""
        if self.dragging:
            dx = x - self.last_x
            dy = y - self.last_y
            
            # Scale panning speed with zoom level - slower panning when zoomed in
            pan_scale = 1.0 / self.zoom
            
            self.scroll_x += dx * pan_scale
            self.scroll_y -= dy * pan_scale  # Invert Y because OpenGL Y is bottom-up
            self.last_x = x
            self.last_y = y
            glutPostRedisplay()

    def keyboard(self, key, x, y):
        """Handle keyboard input for additional controls."""
        if key == b'r' or key == b'R':
            # Reset view
            self.zoom = 1.0
            self.scroll_x = 0
            self.scroll_y = 0
            self.calculate_node_positions()
            glutPostRedisplay()
        elif key == b'+' or key == b'=':
            # Zoom in
            old_zoom = self.zoom
            self.zoom = min(self.zoom + self.zoom_factor, self.max_zoom_in)
            if self.zoom != old_zoom:
                self.calculate_node_positions()
                glutPostRedisplay()
        elif key == b'-' or key == b'_':
            # Zoom out
            old_zoom = self.zoom
            self.zoom = max(self.zoom - self.zoom_factor, self.max_zoom_out)
            if self.zoom != old_zoom:
                self.calculate_node_positions()
                glutPostRedisplay()
        elif key == b'\x1b':  # Escape key
            print("Exiting visualization...")
            sys.exit(0)

    def reshape(self, width, height):
        """Handle window reshape."""
        self.screen_width = width
        self.screen_height = height
        glViewport(0, 0, width, height)
        glOrtho(0, width, 0, height, -1, 1)
        
        # Recalculate positions for new window size
        self.calculate_node_positions()
        glutPostRedisplay()

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

    def get_zoom_level_description(self):
        """Get a description cu niveluri extinse de zoom."""
        if self.zoom >= 2.0:
            return "Maximum close-up"
        elif self.zoom >= 1.5:
            return "Close-up view"
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
        """Get font size that adapts to zoom level - îmbunătățit."""
        # Calculează o dimensiune efectivă de font bazată pe zoom
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

    def schedule_redraw(self):
        """Schedule a redraw of the visualization."""
        self.needs_redraw = True

    def check_redraw(self):
        """Check if a redraw is needed and reset the flag."""
        if self.needs_redraw:
            self.needs_redraw = False
            return True
        return False

    def idle(self):
        """Idle function for continuous updates."""
        # This can be used for animations or periodic updates
        # For now, we'll just check if we need to redraw
        if self.needs_redraw:
            glutPostRedisplay()

    def display(self):
        """Main display function with zoom optimizations."""
        # Check if we need to redraw
        self.check_redraw()
        
        # Apply zoom-specific rendering optimizations
        self.optimize_rendering_for_zoom()
        
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.root:
            # Draw the tree
            self.draw_tree()
            
            # Draw help text (only if zoom allows)
            self.draw_help_text()
            
            # Draw zoom level indicator
            self.draw_zoom_indicator()
                
        glutSwapBuffers()

    def draw_zoom_indicator(self):
        """Draw a zoom level indicator in the corner - DOAR la zoom >= 1.0."""
        if self.zoom < 1.0:
            return  # Nu afișa zoom indicator sub zoom 1.0
            
        text_alpha = max(0.3, self.get_text_alpha())  # Always somewhat visible
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
        
        # Zoom level indicator
        zoom_progress = (self.zoom - self.max_zoom_out) / (self.max_zoom_in - self.max_zoom_out)
        zoom_progress = max(0, min(1, zoom_progress))
        indicator_x = bar_x + zoom_progress * bar_width
        
        glColor4f(0.0, 0.8, 0.0, text_alpha)
        glBegin(GL_QUADS)
        glVertex2f(bar_x, bar_y)
        glVertex2f(indicator_x, bar_y)  
        glVertex2f(indicator_x, bar_y + bar_height)
        glVertex2f(bar_x, bar_y + bar_height)
        glEnd()

    def highlight_path_for_data(self, data_values, column_names):
        """Highlight the path that would be taken for given data values."""
        if not self.root:
            return
        
        # Clear current path and find new path
        path = self._find_path_for_data(self.root, data_values, column_names)
        
        with self.path_lock:
            # Add all nodes in the path to highlighted paths
            for node in path:
                node_id = id(node)
                self.highlighted_paths.add(node_id)
                # Increment visit count
                self.node_visit_counts[node_id] = self.node_visit_counts.get(node_id, 0) + 1
            
            self.current_path = path
        
        # Trigger redraw
        self.schedule_redraw()

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
            
            # If we couldn't parse the condition, just take the first child
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