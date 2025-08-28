
import tkinter as tk
from tkinter import scrolledtext
import threading, queue

AGENTS = [
	("Proc", "#e6f7ff"),
	("GuardRail", "#fffbe6"),
	("AnomalyModel", "#ffe6e6"),
	("Manager", "#e6ffe6"),
	("KRetriever", "#e6e6ff"),
	("HRetriever", "#f0e6ff"),
	("Notify", "#f7e6ff"),
]

class PipelineGUI(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Pipeline Evolution Viewer")
		self.geometry("900x900")
		self.agent_boxes = {}
		self.log_queue = queue.Queue()
		self._build_ui()
		self.after(100, self._poll_logs)

	def _build_ui(self):
		for idx, (agent, color) in enumerate(AGENTS):
			frame = tk.LabelFrame(self, text=agent, bg=color, padx=5, pady=5)
			frame.grid(row=idx, column=0, sticky="nsew", padx=5, pady=5)
			txt = scrolledtext.ScrolledText(frame, width=80, height=8, bg=color, wrap=tk.WORD)
			txt.pack(fill=tk.BOTH, expand=True)
			self.agent_boxes[agent] = txt
		self.grid_columnconfigure(0, weight=1)
		for i in range(len(AGENTS)):
			self.grid_rowconfigure(i, weight=1)

	def gui_log(self, agent, msg):
		self.log_queue.put((agent, msg))

	def _poll_logs(self):
		while not self.log_queue.empty():
			agent, msg = self.log_queue.get()
			box = self.agent_boxes.get(agent)
			if box:
				box.insert(tk.END, msg + "\n")
				box.see(tk.END)
		self.after(100, self._poll_logs)

# Esempio di uso standalone
if __name__ == "__main__":
	gui = PipelineGUI()

	# Simulazione log (da sostituire con chiamate reali dalla pipeline)
	import time
	def fake_pipeline():
		import random
		for i in range(30):
			agent = AGENTS[random.randint(0, len(AGENTS)-1)][0]
			gui.gui_log(agent, f"Step {i+1}: evento per {agent}")
			time.sleep(0.2)
	threading.Thread(target=fake_pipeline, daemon=True).start()

	gui.mainloop()
