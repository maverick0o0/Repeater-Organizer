import threading
import time
import re
from burp import IBurpExtender, ITab, IExtensionStateListener
from javax.swing import JPanel, JButton, JLabel, JComboBox, BoxLayout, SwingUtilities, JTabbedPane, BorderFactory, JCheckBox, JDialog, JTextField, JEditorPane
from javax.swing.text import JTextComponent
from java.awt import BorderLayout, FlowLayout, Frame
from java.lang import Runnable

class RunOnEDT(Runnable):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def run(self):
        self.func(*self.args, **self.kwargs)

class BurpExtender(IBurpExtender, ITab, IExtensionStateListener):
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        
        callbacks.setExtensionName("Repeater Organizer")
        
        self.naming_method = "Smart Naming"
        self.running = True
        
        self.initUI()
        callbacks.addSuiteTab(self)
        
        callbacks.registerExtensionStateListener(self)
        
        # Start background thread
        self.bg_thread = threading.Thread(target=self.auto_rename_loop)
        self.bg_thread.daemon = True
        self.bg_thread.start()
        
        callbacks.printOutput("Repeater Organizer Loaded Successfully.")
        callbacks.printOutput("Background thread for auto-renaming started.")

    def extensionUnloaded(self):
        self.running = False
        self._callbacks.printOutput("Repeater Organizer Unloaded. Background thread stopped.")

    def getTabCaption(self):
        return "Repeater Organizer"

    def getUiComponent(self):
        return self.main_panel

    def initUI(self):
        self.main_panel = JPanel(BorderLayout(10, 10))
        self.main_panel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15))
        
        # --- Global Actions Panel ---
        global_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        global_panel.setBorder(BorderFactory.createTitledBorder("Global Actions"))
        
        self.enable_checkbox = JCheckBox("Enable Background Auto-Naming", True)
        global_panel.add(self.enable_checkbox)
        
        org_button = JButton("Organize Existing Tabs", actionPerformed=self.organize_all_tabs_event)
        global_panel.add(org_button)
        
        reset_button = JButton("Reset to Numbers", actionPerformed=self.reset_all_tabs_event)
        global_panel.add(reset_button)
        
        # --- Naming Configuration Panel ---
        config_panel = JPanel()
        config_panel.setLayout(BoxLayout(config_panel, BoxLayout.Y_AXIS))
        config_panel.setBorder(BorderFactory.createTitledBorder("Naming Configuration"))
        
        # Row 1: Method
        row1 = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        row1.add(JLabel("Naming Engine: "))
        self.method_combo = JComboBox(["Smart Naming", "Custom Format"])
        self.method_combo.addActionListener(lambda e: self.update_ui_state())
        row1.add(self.method_combo)
        config_panel.add(row1)
        
        # Row 2: Smart Naming Options
        self.smart_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        self.host_prefix_checkbox = JCheckBox("Include [HOST] Prefix", False)
        self.method_prefix_checkbox = JCheckBox("Include Method Prefix", False)
        self.query_checkbox = JCheckBox("Include Query Params", False)
        self.smart_panel.add(self.host_prefix_checkbox)
        self.smart_panel.add(self.method_prefix_checkbox)
        self.smart_panel.add(self.query_checkbox)
        config_panel.add(self.smart_panel)
        
        # Smart Naming Guide
        self.smart_guide_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        smart_guide_text = "<html><div style='padding: 5px;'>" \
                     "<b style='color: #4caf50;'>Smart Naming Guide:</b><br>" \
                     "<code>[HOST] Prefix</code> : Adds the target domain at the start (e.g. [api] /users)<br>" \
                     "<code>Method Prefix</code> : Adds the HTTP method (e.g. POST /users)<br>" \
                     "<code>Query Params</code> &nbsp;&nbsp;: Appends query strings, safely truncating long values (e.g. /users?id=123)<br>" \
                     "</div></html>"
        self.smart_guide_label = JEditorPane("text/html", smart_guide_text)
        self.smart_guide_label.setEditable(False)
        self.smart_guide_label.setOpaque(False)
        self.smart_guide_label.putClientProperty("JEditorPane.honorDisplayProperties", True)
        self.smart_guide_panel.add(self.smart_guide_label)
        config_panel.add(self.smart_guide_panel)
        
        # Row 3: Custom Format Field
        self.custom_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        self.custom_panel.add(JLabel("Format String: "))
        self.custom_format_field = JTextField("{method} {path}", 40)
        self.custom_panel.add(self.custom_format_field)
        config_panel.add(self.custom_panel)
        
        # Row 4: Custom Format Guide
        self.guide_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 5))
        guide_text = "<html><div style='padding: 5px;'>" \
                     "<b style='color: #ff9800;'>Custom Format Guide:</b><br>" \
                     "<code>{method}</code> : HTTP Method (e.g. GET)<br>" \
                     "<code>{host}</code> : Target Domain (e.g. api.target.com)<br>" \
                     "<code>{fullpath}</code> : The complete URL path<br>" \
                     "<code>{path}</code> : A path segment. Stack them for more: <code>{path}{path}</code> = last 2 segments<br>" \
                     "<code>{endpoint}</code> : The very last segment of the path<br>" \
                     "<code>{query}</code> : The query string (e.g. ?id=123)<br>" \
                     "<br><i>Examples:</i><br>" \
                     "<span style='color: #4caf50;'>[{method}] {host}{path}{path}</span> &rarr; [POST] api.target.com/v1/users<br>" \
                     "<span style='color: #4caf50;'>{endpoint}{query} ({method})</span> &rarr; users?id=123 (POST)" \
                     "</div></html>"
        self.guide_label = JEditorPane("text/html", guide_text)
        self.guide_label.setEditable(False)
        self.guide_label.setOpaque(False)
        self.guide_label.putClientProperty("JEditorPane.honorDisplayProperties", True)
        self.guide_panel.add(self.guide_label)
        config_panel.add(self.guide_panel)
        
        # Combine
        center_panel = JPanel(BorderLayout(0, 10))
        center_panel.add(global_panel, BorderLayout.NORTH)
        center_panel.add(config_panel, BorderLayout.CENTER)
        
        self.main_panel.add(center_panel, BorderLayout.NORTH)
        
        self.update_ui_state() # Initialize visibility

    def update_ui_state(self):
        is_custom = (self.method_combo.getSelectedItem() == "Custom Format")
        if hasattr(self, 'smart_panel'): self.smart_panel.setVisible(not is_custom)
        if hasattr(self, 'smart_guide_panel'): self.smart_guide_panel.setVisible(not is_custom)
        if hasattr(self, 'custom_panel'): self.custom_panel.setVisible(is_custom)
        if hasattr(self, 'guide_panel'): self.guide_panel.setVisible(is_custom)

    def organize_all_tabs_event(self, event):
        self._callbacks.printOutput("Organizing all tabs...")
        threading.Thread(target=self.process_tabs, args=(True, False)).start()

    def reset_all_tabs_event(self, event):
        self._callbacks.printOutput("Resetting all tabs to numbers...")
        threading.Thread(target=self.process_tabs, args=(True, True)).start()

    def auto_rename_loop(self):
        while self.running:
            try:
                self.process_tabs(force_all=False, reset=False)
            except Exception as e:
                self._callbacks.printError("Error in background thread: " + str(e))
            time.sleep(2.0)

    def process_tabs(self, force_all=False, reset=False):
        if not force_all and not self.enable_checkbox.isSelected():
            return
            
        try:
            frames = Frame.getFrames()
            burp_frame = None
            for f in frames:
                if f.isVisible() and "Burp Suite" in f.getTitle():
                    burp_frame = f
                    break
                    
            if not burp_frame:
                if force_all: self._callbacks.printError("Could not find Burp Suite main frame.")
                return
                
            loading_dialog = [None]
            if force_all:
                def show_loading():
                    d = JDialog(burp_frame, "Repeater Organizer", False)
                    p = JPanel()
                    p.setBorder(BorderFactory.createEmptyBorder(20, 50, 20, 50))
                    msg = "Resetting tabs to numbers..." if reset else "Organizing tabs, please wait..."
                    p.add(JLabel(msg))
                    d.add(p)
                    d.pack()
                    d.setLocationRelativeTo(burp_frame)
                    d.setVisible(True)
                    loading_dialog[0] = d
                SwingUtilities.invokeAndWait(RunOnEDT(show_loading))

            main_pane = self._find_jtabbedpane_with_tab(burp_frame, "Repeater")
            if not main_pane:
                if force_all: self._callbacks.printError("Could not find main tab pane with 'Repeater' tab.")
                return
                
            repeater_panel = None
            for i in range(main_pane.getTabCount()):
                if main_pane.getTitleAt(i) == "Repeater":
                    repeater_panel = main_pane.getComponentAt(i)
                    break
                    
            if not repeater_panel:
                if force_all: self._callbacks.printError("Could not find Repeater panel component.")
                return
                
            # Find all JTabbedPanes inside Repeater
            panes = []
            self._find_all_jtabbedpanes(repeater_panel, panes)
            
            if force_all: self._callbacks.printOutput("Found %d tabbed panes inside Repeater." % len(panes))
            
            renamed_count = 0
            
            for pane in panes:
                tab_count = pane.getTabCount()
                if tab_count == 0:
                    continue
                    
                # Skip sub-panes like Request/Response viewers or Inspector
                first_title = pane.getTitleAt(0)
                if first_title in ["Pretty", "Raw", "Inspector", "Request", "Response", "Headers"]:
                    continue
                    
                original_index = pane.getSelectedIndex()
                    
                for i in range(tab_count):
                    title = pane.getTitleAt(i)
                    if not force_all and not (title and title.isdigit()):
                        continue
                        
                    if force_all:
                        # Fast synchronous load on EDT (No sleep!)
                        SwingUtilities.invokeLater(RunOnEDT(self._fast_rename_tab_edt, pane, i, title, reset))
                    else:
                        # Background mode for newly clicked/added tabs
                        comp = pane.getComponentAt(i)
                        if comp:
                            request_text = self.extract_request_from_tab(comp)
                            if request_text:
                                smart_name = self.generate_smart_name(request_text)
                                if smart_name and smart_name != title:
                                    SwingUtilities.invokeLater(RunOnEDT(pane.setTitleAt, i, smart_name))
                                    renamed_count += 1
                        
                # Restore original selected tab if we flickered
                if force_all and original_index != -1 and original_index < tab_count:
                    SwingUtilities.invokeLater(RunOnEDT(pane.setSelectedIndex, original_index))
                            
            if force_all: 
                if loading_dialog[0]:
                    SwingUtilities.invokeLater(RunOnEDT(loading_dialog[0].dispose))
                self._callbacks.printOutput("Process complete.")
        except Exception as e:
            self._callbacks.printError("Error in process_tabs: " + str(e))

    def _fast_rename_tab_edt(self, pane, index, title, reset):
        try:
            if reset:
                # Use a zero-width space prefix so .isdigit() is False
                # This prevents the background thread from automatically renaming it again when clicked!
                pane.setTitleAt(index, u"\u200B" + str(index + 1))
                return

            pane.setSelectedIndex(index)
            comp = pane.getComponentAt(index)
            if comp:
                request_text = self.extract_request_from_tab(comp)
                if request_text:
                    smart_name = self.generate_smart_name(request_text)
                    if smart_name and smart_name != title:
                        pane.setTitleAt(index, smart_name)
        except Exception as e:
            self._callbacks.printError("Error in _fast_rename_tab_edt: " + str(e))

    def extract_request_from_tab(self, tab_component):
        text_comps = []
        self._collect_all_jtextcomponents(tab_component, text_comps)
        for text_comp in text_comps:
            text = text_comp.getText()
            if text and any(text.startswith(m) for m in ["GET ", "POST ", "PUT ", "DELETE ", "OPTIONS ", "PATCH ", "HEAD "]):
                return text
        return None

    def _collect_all_jtextcomponents(self, container, result_list):
        if isinstance(container, JTextComponent):
            result_list.append(container)
        if hasattr(container, 'getComponents'):
            for comp in container.getComponents():
                self._collect_all_jtextcomponents(comp, result_list)



    def _find_jtabbedpane_with_tab(self, container, tab_name):
        if isinstance(container, JTabbedPane):
            for i in range(container.getTabCount()):
                if container.getTitleAt(i) == tab_name:
                    return container
        if hasattr(container, 'getComponents'):
            for comp in container.getComponents():
                res = self._find_jtabbedpane_with_tab(comp, tab_name)
                if res: return res
        return None

    def _find_all_jtabbedpanes(self, container, result_list):
        if isinstance(container, JTabbedPane):
            result_list.append(container)
        if hasattr(container, 'getComponents'):
            for comp in container.getComponents():
                self._find_all_jtabbedpanes(comp, result_list)

    def generate_smart_name(self, request_text):
        try:
            method = "GET"
            path = "/"
            
            lines = request_text.split('\n')
            if not lines:
                return "Unknown"
            
            # Simple fallback path extraction
            first_line = lines[0].strip()
            path_start = first_line.find(" ")
            path_end = first_line.rfind(" HTTP")
            if path_start != -1 and path_end != -1:
                method = first_line[:path_start].strip()
                path = first_line[path_start+1:path_end].strip()
                
            # Extract Host
            host = ""
            for line in lines[1:]:
                if line.lower().startswith("host:"):
                    host = line[5:].strip()
                    break

            query = ""
            if '?' in path:
                q_str = path.split('?', 1)[1]
                params = q_str.split('&')
                trunc_params = []
                for p in params:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        if len(v) > 3:
                            v = v[:3] + "..."
                        trunc_params.append(k + "=" + v)
                    else:
                        if len(p) > 3:
                            p = p[:3] + "..."
                        trunc_params.append(p)
                query = "?" + "&".join(trunc_params)
            
            base_path = path.split('?')[0]
            endpoint_segments = []
            for p in base_path.split('/'):
                if not p: continue
                if len(p) > 20:
                    p = p[:3] + "..."
                endpoint_segments.append(p)

            # Safely fetch UI state
            ui_state = [None, None, False, False, False]
            def fetch_ui():
                ui_state[0] = self.method_combo.getSelectedItem()
                ui_state[1] = self.custom_format_field.getText()
                ui_state[2] = self.host_prefix_checkbox.isSelected()
                ui_state[3] = self.method_prefix_checkbox.isSelected()
                ui_state[4] = self.query_checkbox.isSelected()
                
            if SwingUtilities.isEventDispatchThread():
                fetch_ui()
            else:
                SwingUtilities.invokeAndWait(RunOnEDT(fetch_ui))
                
            naming_method, fmt, host_prefix, method_prefix, query_enabled = ui_state
            
            if naming_method == "Custom Format":
                
                endpoint = endpoint_segments[-1] if endpoint_segments else "/"
                
                # Handle {path} stacking
                def path_replacer(match):
                    count = match.group(0).count('{path}')
                    if len(endpoint_segments) > count:
                        return "/" + "/".join(endpoint_segments[-count:])
                    else:
                        return "/" + "/".join(endpoint_segments)
                
                result = re.sub(r'(\{path\})+', path_replacer, fmt)
                
                result = result.replace("{fullpath}", base_path)
                result = result.replace("{method}", method)
                result = result.replace("{host}", host)
                result = result.replace("{endpoint}", endpoint)
                result = result.replace("{query}", query)
                
                return result if result else "/"

            # ===== Smart Naming Logic =====
            
            if len(endpoint_segments) > 3:
                clean_path = "/" + "/".join(endpoint_segments[-3:])
            else:
                clean_path = "/" + "/".join(endpoint_segments)
                
            if clean_path == "" or clean_path == "/":
                clean_path = "/"
                
            # Include the safely truncated query string
            if query and query_enabled:
                clean_path += query
                
            final_name = clean_path
            
            # Extract subdomain/domain prefix
            domain_parts = host.split('.')
            prefix = host
            if len(domain_parts) >= 2:
                if domain_parts[0] == "www":
                    prefix = domain_parts[1]
                else:
                    prefix = domain_parts[0]
            
            if host_prefix:
                final_name = "[%s] %s" % (prefix, final_name)
                
            if method_prefix:
                final_name = "%s %s" % (method, final_name)
                
            return final_name
        except Exception as e:
            self._callbacks.printError("Error generating name: " + str(e))
            return None
