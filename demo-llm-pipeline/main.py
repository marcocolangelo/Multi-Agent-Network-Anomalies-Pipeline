from app.GUI import PipelineGUI
import threading
import asyncio
from test_pipeline import test_pipeline
from app.utils.tracing import init_logger
import app.global_gui

# Crea l'istanza globale della GUI
app.global_gui.gui = PipelineGUI()
gui = app.global_gui.gui

def run_pipeline():
    init_logger()
    asyncio.run(test_pipeline())
    # gui.after(100, gui.destroy)  # chiude la GUI

if __name__ == "__main__":
    threading.Thread(target=run_pipeline, daemon=True).start()
    gui.mainloop()
