"""
FasttGantt: A Gantt Chart graphic generator
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, PhotoImage
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.patches as matplotptchs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np

# TODO: sort earliest dateto include the today date
# TODO: subtask
# DEBUG: new task that is before project start is a problem...
#        to do with ticks working from first item..  need to recalculate
#        all positions and include vertical line for date
class TeamListManager(tk.Toplevel):
    """
    Manages the Team list

    Parameters:
    tk.Toplevel : Pointer to the root tk object
    """
    def __init__(self, parent, team_list, assigned, callback):
        """
        Init the Team list Dialog box

        Parameters:
        team_list : the existing list of team/people on the project
        assigned : list of teams that have been assigned a task (and cannot be deleted)
        callback : pointer to a function that updates the team list
        """
        super().__init__(parent)
        self.callback = callback
        self.old_list = team_list
        self.team_list = team_list
        self.assigned = assigned
        self.parent = parent
        self.title("Add/Remove Team Members")
        ttk.Label(self, text="Enter Team Name:")
        self.entry = tk.Entry(self, width=30)
        self.entry.pack(pady=10)
        self.add_button = tk.Button(self, text="Add", command=self.add_entry)
        self.add_button.pack(pady=5)
        ttk.Label(self, text="Teams Members:")
        self.listbox = tk.Listbox(self, width=30, height=10) # selectmode=tk.MULTIPLE,
        self.listbox.pack(pady=10)

        for item in self.team_list:
            self.listbox.insert(tk.END, item)

        self.delete_button = tk.Button(self, text="Delete", command=self.delete_entry)
        self.delete_button.pack(pady=5)

        self.done_button = tk.Button (self, text="Done", command=self.done)
        self.done_button.pack(pady=5)

        self.cancel_button = tk.Button (self, text="Cancel", command=self.cancel)
        self.cancel_button.pack(pady=5)

    def add_entry(self):
        """
        Adds a new team member 
        """
        new_entry = self.entry.get()
        if new_entry:
            if new_entry in self.team_list:
                messagebox.showwarning("Input Error", "Team members must have unique names")
                return
            self.listbox.insert(tk.END, new_entry)
            self.team_list.append(new_entry)
            self.entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Input Error", "Blank team members not allowed")

    def delete_entry(self):
        """
        Removes a team member that is not in the assigned list
        """
        selected_items = self.listbox.curselection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select an item to delete.")
            return
        for index in selected_items[::-1]:
            if self.team_list[index] in self.assigned:
                messagebox.showwarning("Still Assigned!",
                                    "Remove a team member from all tasks before deleting.")
            else:
                self.team_list.pop(index)
                self.listbox.delete(index)

    def done(self):
        """
        Update team through callback function. Close dialog
        """
        self.callback(self.team_list)
        self.destroy()  # Close the dialog

    def cancel(self):
        """
        Revert to the original list. Close dialog
        """
        self.callback(self.old_list)
        self.destroy()  # Close the dialog

class AboutDialog(tk.Toplevel):
    """
    A dialog to show the 'about' information
    """
    def __init__(self, parent):
        """
        Creates a Dialog box with basic project info
        """
        super().__init__(parent)
        self.title("App Information")
        self.geometry("800x600")
        self.resizable(False, False)

        self.label_intro = ttk.Label(self, text="this software brought to you by:")
        self.label_intro.pack(pady=5)

        self.app_logo = PhotoImage(file="./docs/pics/paramita-logo.png")
        self.label_logo = tk.Label(self, image=self.app_logo)
        self.label_logo.pack(pady=10)

        self.label_copyright = ttk.Label(self, text="Copyright © 2024 Paramita ltd")
        self.label_copyright.pack(pady=5)

        self.label_license = ttk.Label(self, text="available under GNU GENERAL PUBLIC LICENSE")
        self.label_license.pack(pady=5)

        self.link_label = tk.Label(self, text="paramita-electronics.org", fg="blue", cursor="hand2")
        self.link_label.pack(pady=10)
        self.link_label.bind("<Button-1>",
                            lambda e: self.open_website("https://www.paramita-electronics.org")
                            )
        self.label_about = ttk.Label(self,
                                    text="Generates pretty Gantt Charts")
        self.label_about.pack(pady=5)
        self.button_ok = ttk.Button(self, text="OK", command=self.destroy)
        self.button_ok.pack(pady=10)

    def open_website(self, link_uri):
        """
        method to open a link in the dialog box.
        """

class GanttChartApp:
    """
    A Simple Gannt Chart creating program
    """
    def on_closing(self):
        """
        Function to handle the window closing event.
        """
        self.root.quit()
        self.root.destroy()

    def __init__(self, tkwin):
        """
        Create the window and setup
        """
        self.root = tkwin
        self.selected_tasks = None
        self.dependee = None
        self.pre_edit_name = None
        self.task_was_start = None
        # Set up the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Set up the window
        self.root.title("Gantt Chart Generator")
        self.project_title = 'Project Management of an Example Project'
        #self.df = pd.read_excel("./default_plan.ods", engine='odf', index_col=0)
        try:
            self.load_file("./default_plan.ods")
        except FileNotFoundError:
            # handle exception
            tk.messagebox.showwarning(title="Unkonwn loading Error",
                                      message="Error loading default project")
            self.df = pd.DataFrame()
            self.team = []
        self.recalculate_task_attributes()
        self.today_date = dt.date.today()
        self.team_colors = self.assign_colors_for_team()

        # Create menu
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Load", command=self.load_file_btn)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Export Image", command=self.export_image)
        file_menu.add_command(label="Export Graphic", command=self.save_plot)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menu.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(self.menu, tearoff=0)
        edit_menu.add_command(label="Set Title", command=self.set_title)
        edit_menu.add_command(label="Set Date Today" , command=self.set_current_date)
        edit_menu.add_command(label="Add/Remove Teams", command=self.show_team_manager)
        self.menu.add_cascade(label="Edit", menu=edit_menu)
        help_menu = tk.Menu(self.menu, tearoff=0)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=lambda: AboutDialog(self.root))
        help_menu.add_separator()
        self.menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=self.menu)


        # Create left pane for task input
        self.left_frame = ttk.Frame(self.root, padding="10")
        self.left_frame.grid(row=0, column=0, sticky="ns")
        self.left_frame.grid_rowconfigure(0, weight=1)

        # Create and configure the style
        small_style = ttk.Style()
        # Adjust the font size
        small_style.configure("Treeview", font=("Helvetica", 9))
        # Adjust the header font
        small_style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

        # Create Treeview for task list
        self.tree = ttk.Treeview(self.left_frame, selectmode='browse') # selectmode='extended')
        self.tree["columns"] = ( "start", "task_duration", "team", "dependencies")
        self.tree.column("#0", width=150, minwidth=150)
        self.tree.column("start", width=100, minwidth=100)
        self.tree.column("task_duration", width=25, minwidth=20)
        self.tree.column("team", width=100, minwidth=100)
        self.tree.column("dependencies", width=80, minwidth=35)
        self.tree.heading("#0", text="Task Name")
        self.tree.heading("start", text="Start")
        self.tree.heading("task_duration", text="days")
        self.tree.heading("team", text="Assignee")
        self.tree.heading("dependencies", text="Depends")
        self.tree.grid(row=0, column=0, columnspan=2, pady=10, sticky='nsew')
        self.tree.bind("<Button-1>", self.select_task)

        self.up_btn  = ttk.Button(self.left_frame, text="↑", command=self.move_task_up)
        self.up_btn.grid(row=1, column=0, pady=5)
        self.up_btn.state(['disabled'])
        self.dependency_mode = False

        self.dwn_btn = ttk.Button(self.left_frame, text="↓", command=self.move_task_down)
        self.dwn_btn.grid(row=1, column=1, pady=5)
        self.dwn_btn.state(['disabled'])
        self.subtask_mode = False

        # Buttons for task dependencies
        self.dep_btn  = ttk.Button(self.left_frame, text="Depends On", command=self.set_dependency)
        self.dep_btn.grid(row=2, column=0, pady=5)
        self.dep_btn.state(['disabled'])
        self.dependency_mode = False

        self.subt_btn = ttk.Button(self.left_frame, text="Subtask Of", command=self.set_subtask)
        self.subt_btn.grid(row=2, column=1, pady=5)
        self.subt_btn.state(['disabled'])
        self.subtask_mode = False


        ttk.Label(self.left_frame, text="Task Name").grid(row=3, column=0)
        ttk.Label(self.left_frame, text="Duration (days)").grid(row=4, column=0)
        ttk.Label(self.left_frame, text="Start Date (YYYY-MM-DD)").grid(row=5, column=0)
        ttk.Label(self.left_frame, text="Assignee").grid(row=6, column=0)
        ttk.Label(self.left_frame, text="Completion").grid(row=7, column=0)

        self.task_name = ttk.Entry(self.left_frame)
        self.task_name.grid(row=3, column=1)
        self.task_duration = ttk.Entry(self.left_frame)
        self.task_duration.grid(row=4, column=1)
        self.task_start = ttk.Entry(self.left_frame)
        self.task_start.grid(row=5, column=1)
        self.task_start.insert(0, dt.date.today())

        self.team_var = tk.StringVar(self.root)
        self.team_var.set(self.team[0]) # default value
        self.task_assignee = tk.OptionMenu(self.left_frame, self.team_var, *self.team)
        self.task_assignee.grid(row=6, column=1, sticky="nsew")

        self.completion_var = tk.DoubleVar()
        self.completion_var.set(0.2)
        self.completion_slider = ttk.Scale(
                self.left_frame,
                from_=0,
                to=1.0,
                orient='horizontal',
                variable=self.completion_var
                )
        self.completion_slider.grid(row=7,column=1, sticky="ew")

        self.new_task_btn = ttk.Button(self.left_frame, text="Add Task", command=self.add_task)
        self.new_task_btn.grid(row=8, column=0)

        self.edit_task_btn = ttk.Button(self.left_frame, text="Edit Task", command=self.edit_task)
        self.edit_task_btn.grid(row=8, column=1)
        self.edit_task_btn.state(['disabled'])

        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.update_treeview()
        self.draw_gantt_chart()

        # Configure grid weights
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

    def edit_task(self):
        """
        Called when the "Edit Task" button is clicked
        """
        try:
            task_name = self.task_name.get()
            if "[]" in task_name:
                raise ValueError('task name must not contain the "[]" string')
            if "," in task_name:
                raise ValueError('task name must not contain the "," character')
            task_duration = int(self.task_duration.get())
            task_start = dt.datetime.strptime(self.task_start.get(), '%Y-%m-%d')
            #task_assignee = self.task_assignee.get()
            task_assignee = self.team_var.get()
            completion = self.completion_var.get()
            row_index = self.get_task_id(self.pre_edit_name)
            self.pre_edit_name = task_name
            #print(task_name)
            #print(self.df.loc[row_index])
            self.df.loc[row_index, 'task'] = task_name
            self.df.loc[row_index, 'team'] = task_assignee
            self.df.loc[row_index, 'start']= pd.Timestamp(task_start)
            self.df.loc[row_index, 'end']=pd.Timestamp(task_start+dt.timedelta(days=task_duration))
            self.df.loc[row_index, 'completion_frac'] = completion
            # if the start date got earlier, recalculate the 'days to start' values
            if self.df['start'].min() == pd.Timestamp(task_start):
                self.recalculate_task_attributes()
            else:
                self.df.loc[row_index,'days_to_start'] = (pd.Timestamp(task_start) - \
                                                           self.df['start'].min()).days
                self.df.loc[row_index,'days_to_end'] = (pd.Timestamp(task_start + \
                                                         dt.timedelta(days=task_duration)) - \
                                                         self.df['start'].min()).days
                #N.B. +1 in task duration to include also the end date
                self.df.loc[row_index,'task_duration'] = self.df.loc[row_index,'days_to_end'] - \
                                                          self.df.loc[row_index,'days_to_start']+1
                self.df.loc[row_index,'completion_days']=self.df.loc[row_index,'completion_frac']*\
                                                          self.df.loc[row_index,'task_duration']

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")
        self.update_treeview()
        self.draw_gantt_chart()

    def recalculate_task_attributes(self):
        """
        Re-calculate the task attributes that depend on the start of the project
        (needed when the earliest date referenced changes)
        """
        self.df['days_to_start'] = (self.df['start'] - \
                                    self.df['start'].min()).dt.days
        self.df['days_to_end'] = (self.df['end'] - self.df['start'].min()).dt.days
        self.df['task_duration'] = self.df['days_to_end'] - \
                                   self.df['days_to_start'] + 1  # to include also the end date
        self.df['completion_days'] = self.df['completion_frac'] * self.df['task_duration']
        self.df = self.df.sort_index()

    def add_task(self):
        """
        Called when the "Add Task" button is clicked
        """
        try:
            task_name = self.task_name.get()
            if "[]" in task_name:
                raise ValueError('task name cannot contain the "[]" string')
            if "," in task_name:
                raise ValueError('task name cannot contain the "," character')
            if task_name in self.df["task"].values:
                raise ValueError('task name must be unique (try selecting and using "edit")')
            task_duration = int(self.task_duration.get())
            task_start = dt.datetime.strptime(self.task_start.get(), '%Y-%m-%d')
            #task_assignee = self.task_assignee.get()
            task_assignee = self.team_var.get()
            completion = self.completion_var.get()

            df_task = [ task_name, task_assignee, pd.Timestamp(task_start), \
                        pd.Timestamp(task_start+dt.timedelta(days=task_duration)), completion, \
                                self.process_column(float('NaN')), \
                                #No Dependencies
                                (task_start - self.df['start'].min()).days, \
                                # calc days before start
                                (task_start+dt.timedelta(days=task_duration) - \
                                self.df['start'].min()).days, \
                                # calc end
                                task_duration, \
                                # duration
                                completion * task_duration,
                                # days completed
                            ]
            self.df.loc[-1] = df_task
            self.df.index = self.df.index + 1
            self.df = self.df.sort_index()
            # if the start date got earlier, recalculate the 'days to start' values
            if self.df['start'].min() == pd.Timestamp(task_start) or self.task_was_start:
                self.recalculate_task_attributes()

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")
        self.update_treeview()
        self.draw_gantt_chart()

    def update_treeview(self):
        """
        Check and update the treeview (the list of tasks in the top LHS)
        """
        self.tree.delete(*self.tree.get_children())
        # Insert DataFrame items into Treeview
        for idx, row in self.df.iterrows():
            self.tree.insert("", "end", text=row['task'],
                             values=(row['start'].strftime('%Y-%m-%d'),
                             row['task_duration'], row['team'], row['dependencies']))
        if self.selected_tasks is not None:
            # update the selected tasks too
            for item in self.tree.get_children():
                #print(self.tree.item(item)['text'])
                #if  self.tree.item(item)['text'] in self.df[self.df['task']] :
                task_id = self.get_task_id(self.tree.item(item)['text'])
                #print(self.selected_tasks)
                if task_id == self.selected_tasks:
                    #print("Got it!")
                    self.tree.selection_set(item)
        else:
            for item in self.tree.get_children():
                if item in self.tree.selection():
                    self.tree.selection_remove(item)

    def remove_alpha(self, color):
        """
        Remove the alpha channel from an RGBA color and return an RGB color.
        Parameters:
        color (str or tuple): Matplotlib color string or RGBA tuple.
        Returns:
        tuple: RGB color.
        """
        rgba_color = plt.cm.colors.to_rgba(color)  # Convert to RGBA tuple
        return (rgba_color[0], rgba_color[1], rgba_color[2], 1.0)  # Return RGB with alpha set to 1


    def draw_gantt_chart(self):
        """
        Uses Matplotlib to draw the Gantt Chart
        """
        #style:
        bar_height = 0.65  # Adjust this value as needed
        bar_spacing = 0.1
        patches = []
        task_hbar_coordinates = {}
        for member, c in self.team_colors.items():
            patches.append(matplotptchs.Patch(color=c))
        self.ax.clear()
        bar_coords = {}
        for index, row in self.df.iterrows():
            completed_bar = self.ax.barh(y=row['task'],
                                         width=row['task_duration'],
                                         left=row['days_to_start'] + 1,
                                         color=self.team_colors[row['team']],
                                         alpha=0.4, height=bar_height)
            full_bar = self.ax.barh(y=row['task'],
                                    width=row['task_duration'],
                                    left=row['days_to_start'] + 1,
                                    color=self.team_colors[row['team']],
                                    alpha=0.4, linewidth=5, height=bar_height)
            outline_bar = self.ax.barh(y=row['task'],
                                       width=row['task_duration'],
                                       left=row['days_to_start'] + 1,
                                       color='none',
                                       edgecolor=self.team_colors[row['team']],
                                       linewidth=1.75,
                                       height=bar_height )
            self.ax.barh(y=row['task'],
                         width=row['completion_days'],
                         left=row['days_to_start'] + 1,
                         color=self.team_colors[row['team']],
                         height=bar_height)
            # Coordinates for annotation
            rect = full_bar.patches[0]  # bar.patches is a list of Rectangle objects
            start = (rect.get_x()+rect.get_width(), rect.get_y() + rect.get_height() / 2)
            end = (rect.get_x(), rect.get_y() )
            bar_coords[row['task']] = [start, end]
        plt.title(self.project_title, fontsize=18)
        # 2
        plt.gca().invert_yaxis()
        # 3
        #TODO: sort earliest date to include the today date
        total_days = ( self.df['end'].max() - self.df['start'].min() ).days
        xticks = np.arange(1, total_days, 7)
        # 4
        xticklabels = pd.date_range(start=self.df['start'].min() + dt.timedelta(days=0),
                                    end=self.df['end'].max()).strftime("%d/%m")
        # 5
        num_tasks =  self.df.shape[0]
        y_positions = np.arange(num_tasks)# * (bar_height + bar_spacing))
        self.ax.set_yticks(y_positions)
        #self.ax.set_yticklabels()
        self.ax.set_xticks(xticks)

        self.ax.set_xticklabels(xticklabels[::7])
        # 6
        self.ax.xaxis.grid(True, alpha=0.5)
        # Adding a legend
        self.ax.legend(handles=patches, labels=self.team_colors.keys(), fontsize=11)
        # Marking the current date on the chart
        horizontal_position = (self.today_date - (self.df['start'].min()).date() ).days
        self.ax.axvline(x=horizontal_position, color='r', linestyle='dashed')
        self.ax.text(x=horizontal_position + 0.5, y=11.5, s=self.today_date, color='r')

        # Add annotation with an arrow
        #print(bar_coords)
        for index, row in self.df.iterrows():
            if row['dependencies']:
                if row['task'] in bar_coords:
                    for dependency in row['dependencies']:
                        # Coordinates for annotation
                        not_used, end = bar_coords[row['task']]
                        start, not_used = bar_coords[dependency]
                        # if the arrow goes straight down, don't use a curvy arrow
                        if start[0]==end[0]: #straight arrow
                            self.ax.annotate(
                                '', xy=end, xytext=start,
                                arrowprops={"arrowstyle":'->',
                                                "lw":2, "color":'black',
                                                "alpha":0.65,
                                                "connectionstyle":"arc3,rad=0."}
                            )
                        else: #(curvy arrow)
                            self.ax.annotate(
                                '', xy=end, xytext=start,
                                arrowprops={"arrowstyle":'->',
                                            "lw":2, "color":'black',
                                            "alpha":0.65,
                                            "connectionstyle":"angle,angleA=0,angleB=-90,rad=10"}
                            )
        # Adjust the subplot parameters to reduce the space on the RHS
        self.figure.subplots_adjust(left=0.1, right=0.85, top=0.9, bottom=0.1)
        # Increase the font size of the y-labels
        self.ax.tick_params(axis='y', labelsize=18)  # Set the font size as desired

        # Adjust the layout to have the graph area around the categories
        self.ax.spines['left'].set_visible(False)  # Hide the left spine
        self.ax.spines['right'].set_visible(False)  # Hide the right spine
        self.ax.spines['top'].set_visible(False)  # Hide the top spine
        self.ax.yaxis.tick_left()  # Move the y-ticks to the left side
        # 'magic' command to make everything fit properly
        plt.tight_layout()
        self.canvas.draw()

    def load_file_btn(self):
        """
        Called when the "Load" menu is clicked
        """
        file_path = filedialog.askopenfilename(defaultextension=".ods")
        if file_path:
            self.load_file(file_path)
            self.update_treeview()
            self.draw_gantt_chart()

    def load_file(self, file_path):
        """
        Loads an ods file of the right format for the project

        Parameters:
        file_path (string): The file path
        """
        # TODO: check for literals '[]' or ',' as these will do bad things!
        self.df = pd.read_excel(file_path, engine='odf', index_col=0)
        self.df['dependencies'] = self.df['dependencies'].apply(self.process_column)
        self.recalculate_task_attributes()
        unique_team_entries = self.df['team'].unique().tolist()
        if len(unique_team_entries) != 0:
            self.team = unique_team_entries

    def process_column(self, cell):
        """
        Convert the empty list "[]" imported as a string back to an empty list 

        Parameters:
        cell (string): comma separated list as a string

        Returns:
        list: a list of values or empty list
        """
        if pd.isna(cell):
            return []
        if "[]" in cell:
            return []
        return cell.split(',')

    def save_file(self):
        """
        Called when the "Save" menu is clicked, dialog that exports to .ods
        """
        file_path = filedialog.asksaveasfilename(defaultextension=".ods")
        if file_path:
            with pd.ExcelWriter(file_path, engine="odf") as doc:
                self.df.to_excel(doc, columns=['task', 'team', 'start',
                                               'end', 'completion_frac','dependencies'],
                                 sheet_name="Sheet1")

    def set_title(self):
        """
        Called when the "Set Title" menu is clicked
        """
        text = tk.simpledialog.askstring(title = "Set Ttile:",
                                         prompt = "Enter the Title for the Gantt Chart:",
                                         initialvalue=self.project_title)
        self.project_title = text
        self.draw_gantt_chart()

    def set_current_date(self):
        """
        Called when the "Set Date Today" menu is clicked
        """
        text = tk.simpledialog.askstring(title = "Set Date:",
                                         prompt = "Red line Date in YYYY-MM-DD format:",
                                         initialvalue=dt.date.today())
        if text is None:
            pass
        elif dt.datetime.strptime(text, '%Y-%m-%d'):
            old_date = self.today_date
            self.today_date = dt.datetime.strptime(text, '%Y-%m-%d').date()
            if self.df['start'].min() > old_date:
                self.recalculate_task_attributes()
            self.draw_gantt_chart()

    def export_image(self):
        """
        Exports a png image. Called when the "Export Image" menu is clicked.
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ]
            )
        if file_path:
            self.figure.savefig(file_path)

    def save_plot(self):
        """
        Exports an image or vector graphic.  Called when the "Export Graphic" menu is clicked
        """
        # Ask for file save location with options for PNG and SVG
        file_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[
                ("SVG files", "*.svg"),
                ("PDF files", "*.pdf"),
                ("PS files", "*.ps"),
                ("EPS files", "*.eps"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("TIFF files", "*.tiff"),
                ("BMP files", "*.bmp"),
                ("RAW files", "*.raw"),
                ("GIF files", "*.gif"),
                ("PGF files", "*.pgf"),
                ("WEBP files", "*.webp")
            ]
        )
        if file_path:
            # Determine the format based on the file extension
            file_ext = file_path.split('.')[-1]
            if file_ext.lower() in ['png', 'svg', 'pdf', 'ps',
                                    'eps', 'jpg', 'jpeg', 'tiff',
                                    'bmp', 'raw', 'gif', 'pgf', 'webp']:
                self.figure.savefig(file_path, format=file_ext.lower())

    def update_string_list(self, new_list):
        """
        Callback function to set the team list.
        """
        self.team = new_list
        #print("Updated string list:", self.string_list)

    def show_team_manager(self):
        """
        Creates a dialog for controlling the team.
        Called when "Add/Remove Team members" menu is clicked
        """
        assigned_list = []
        for member in self.team:
            if member in self.df['team'].values :
                assigned_list.append(member)
        updated_list = TeamListManager(self.root, self.team, assigned_list, self.update_string_list)
        self.root.wait_window(updated_list)
        #self.team = updated_list
        self.task_assignee['menu'].delete(0, 'end')  # Delete all options from the menu
        ## Update with new options
        for person in self.team:
            self.task_assignee['menu'].add_command(label=person,
                                                   command=tk._setit(self.team_var, person))
        self.team_colors = self.assign_colors_for_team()

    def assign_colors_for_team(self):
        """
        Sets a color for each member of the team
        """
        #qualitative_colors = cm.Dark2.colors + cm.Set3.colors
        qualitative_colors = plt.get_cmap('Dark2').colors + plt.get_cmap('Set3').colors
        num_cols = len(qualitative_colors)
        if len(self.team) >  num_cols:
            print("warning: more team members than colors! Some will repeat")
        offset = 0
        team_colors = {}
        #for i in range(len(self.team)):
        #    team_colors[self.team[i]] = qualitative_colors[(i+offset)%num_cols]
        for i, tm in enumerate(self.team):
            team_colors[tm] = qualitative_colors[(i+offset)%num_cols]
        return team_colors

    def set_dependency(self):
        """
        Called when "Depends On" button clicked.
        Sets dependency_mode and changes UI
        so that when a task is selected in the treeview 
        it is set as a dependency of the current selection
        """
        if self.selected_tasks is not None:
            self.dependee = self.selected_tasks
            self.dependency_mode = True
            self.subtask_mode = False
            # Grey out the other boxes
            self.up_btn.state(['disabled'])
            self.dwn_btn.state(['disabled'])
            self.dep_btn.state(['disabled'])
            self.task_name.state(['disabled'])
            self.task_duration.state(['disabled'])
            self.task_start.state(['disabled'])
            #self.task_assignee.state(['disabled'])
            menu = self.task_assignee.nametowidget(self.task_assignee.menuname)
            for i in range(len(self.team)):
                menu.entryconfig(i, state="disabled")
            self.completion_slider.state(['disabled'])
            self.new_task_btn.state(['disabled'])
            self.edit_task_btn.state(['disabled'])

    def set_subtask(self):
        """
        Unimplemented feature, called when the "Subtask Of" button is clicked
        """
        print("not implemented")
        if self.selected_tasks is not None:
            self.dependency_mode = False
            self.subtask_mode = True
            # Grey out the other boxes
            self.up_btn.state(['disabled'])
            self.dwn_btn.state(['disabled'])
            self.dep_btn.state(['disabled'])
            self.task_name.state(['disabled'])
            self.task_duration.state(['disabled'])
            self.task_start.state(['disabled'])
            #self.task_assignee.state(['disabled'])
            menu = self.task_assignee.nametowidget(self.task_assignee.menuname)
            for i in range(len(self.team)):
                menu.entryconfig(i, state="disabled")
            self.completion_slider.state(['disabled'])
            self.new_task_btn.state(['disabled'])
            self.edit_task_btn.state(['disabled'])

    def move_task_up(self):
        """
        Moves a task up in the df and tree.  Called when "up arrow" button is clicked
        """
        #TODO: DEBUG: Comments here are an attempt at multiple
        # selection code that doesn't work because treeview won't select
        # more than one item...
        #if min(self.selected_tasks) == 0:
        if self.selected_tasks == 0:
            return
        new_indices = self.selected_tasks-1 #[i-1 for i in self.selected_tasks]
        temp_df = self.df.copy()
        #for old, new in zip(self.selected_tasks, new_indices):
        #    temp_df.iloc[new], temp_df.iloc[old] = self.df.iloc[old], self.df.iloc[new]
        old = self.selected_tasks
        new = new_indices
        temp_df.iloc[new], temp_df.iloc[old] = self.df.iloc[old], self.df.iloc[new]
        self.df = temp_df
        self.selected_tasks = new_indices
        # show the results
        self.update_treeview()
        self.draw_gantt_chart()
        return

    def move_task_down(self):
        """
        Moves a task down in the df and tree.  Called when "down arrow" button is clicked
        """
        if self.selected_tasks == len(self.df)-1:
            return
        new_indices = self.selected_tasks+1 #[i-1 for i in self.selected_tasks]
        temp_df = self.df.copy()
        #for old, new in zip(self.selected_tasks, new_indices):
        #    temp_df.iloc[new], temp_df.iloc[old] = self.df.iloc[old], self.df.iloc[new]
        old = self.selected_tasks
        new = new_indices
        temp_df.iloc[new], temp_df.iloc[old] = self.df.iloc[old], self.df.iloc[new]
        self.df = temp_df
        self.selected_tasks = new_indices
        # show the results
        self.update_treeview()
        self.draw_gantt_chart()
        return

    def get_task_id(self, name):
        """
        Get index of the task with the same name in self.df

        Parameters:
        name (string): Task name.
 
        Returns:
        int: index of the task.
        """
        result = self.df[self.df['task'] == name]
        if not result.empty:
            #return result.iloc[0]['id']
            return result.index[0]
        return None

    def select_task(self, event):
        """
        Called when the treeview is clicked.
        - Checks if the dependency or subtask mode is set and responds appropriately.
        - Sets or clears GUI tasks associated with  selected/deselected tasks

        Parameters:
        event (Event): The click Event
        """
        item = self.tree.identify('item', event.x, event.y)
        #item_info = self.tree.item(item)
        task_name = self.tree.item(item)['text'] # task name is the unique identifier
        task_id = self.get_task_id(task_name)
        # item relates to the tree
        # use task name to find it in the dataframe
        if item:
            reset_selected_tasks = False
            set_selected_tasks = False
            index_to_set = 0
            if self.dependency_mode:
                if task_name in self.df.at[self.dependee, 'dependencies']:
                    self.df.at[self.dependee, 'dependencies'].remove(task_name)
                else:
                    self.df.at[self.dependee, 'dependencies'].append(task_name)
                reset_selected_tasks = True
                self.dependency_mode = False
                self.subtask_mode = False
                self.dependee = None
            elif self.subtask_mode:
                #TODO: subtasks logic
                #self.tasks[self.selected_tasks]["subtasks"].append(task_index)
                reset_selected_tasks = True
                self.subtask_mode = False
                self.dependency_mode = False
            else:
                #deselect if second click
                if self.selected_tasks is not None:
                    if task_id == self.selected_tasks:
                        reset_selected_tasks = True
                    else:
                        # add selected task to existing list
                        #DEBUG:  Multiple task selection in treeview!
                        # select new
                        set_selected_tasks = True
                        index_to_set = task_id
                else:
                    #add selected task to new list
                    #self.selected_tasks = [task_id]
                    set_selected_tasks = True
                    index_to_set = task_id

            if reset_selected_tasks:
                self.selected_tasks = None
                # Deselect item
                selected_items = self.tree.selection()
                if selected_items:
                    self.tree.selection_remove(selected_items[0])
                self.update_treeview()
                self.up_btn.state(['disabled'])
                self.dwn_btn.state(['disabled'])
                self.dep_btn.state(['disabled'])
                self.dependency_mode = False
                self.subt_btn.state(['disabled'])
                self.subtask_mode = False
                self.task_name.state(['!disabled'])
                self.task_duration.state(['!disabled'])
                self.task_start.state(['!disabled'])
                menu = self.task_assignee.nametowidget(self.task_assignee.menuname)
                for i in range(len(self.team)):
                    menu.entryconfig(i, state="active")
                self.completion_slider.state(['!disabled'])
                self.new_task_btn.state(['!disabled'])
                self.edit_task_btn.state(['disabled'])
                self.task_name.delete(0, tk.END)
                self.task_duration.delete(0, tk.END)
                self.task_start.delete(0,tk.END)
                self.task_start.insert(0, dt.date.today())
                self.team_var.set(self.team[0])
                self.completion_var.set(0.5)

            elif set_selected_tasks:
                self.selected_tasks = index_to_set
                #disable "Add Task" enable othersup
                self.up_btn.state(['!disabled'])
                self.dwn_btn.state(['!disabled'])
                self.dep_btn.state(['!disabled'])
                self.subt_btn.state(['disabled']) # not implemented!
                self.task_name.state(['!disabled'])
                self.task_duration.state(['!disabled'])
                self.task_start.state(['!disabled'])
                menu = self.task_assignee.nametowidget(self.task_assignee.menuname)
                for i in range(len(self.team)):
                    menu.entryconfig(i, state="active")
                self.completion_slider.state(['!disabled'])
                self.new_task_btn.state(['disabled'])
                self.edit_task_btn.state(['!disabled'])
                # Set the values
                # (delete them first)
                self.task_name.delete(0, tk.END)
                self.task_duration.delete(0, tk.END)
                self.task_start.delete(0,tk.END)
                row = self.df.iloc[index_to_set]
                #keep this info in case it gets edited
                self.pre_edit_name = row['task']
                if self.df['start'].min() == pd.Timestamp(row['start']):
                    # task keep a record that this was the first task so that
                    # you can re-order ticks on the graph
                    self.task_was_start = True
                else:
                    self.task_was_start = False
                self.task_name.insert(0, row['task'])
                self.task_duration.insert(0, row['task_duration'])
                self.task_start.insert(0, row['start'].strftime('%Y-%m-%d'))
                self.team_var.set(row['team'])
                self.completion_var.set(row['completion_frac'])
                self.edit_task_btn.state(["!disabled"])
            self.update_treeview()
            self.draw_gantt_chart()

if __name__ == "__main__":
    window = tk.Tk()
    app = GanttChartApp(window)
    window.mainloop()
