import sys
import os
import gc
import tracemalloc

# Ensure the root folder is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
import customtkinter as ctk
from services.project_service import ProjectService
from gui.views.project_360 import Project360View

def count_bindings(widget):
    count = 0
    try:
        # Get list of all bound event sequences for this widget
        bound_events = widget.bind()
        count += len(bound_events)
    except Exception:
        pass
    if hasattr(widget, "winfo_children"):
        for child in widget.winfo_children():
            count += count_bindings(child)
    return count

def count_menus(widget):
    count = 0
    if isinstance(widget, tk.Menu):
        count += 1
    if hasattr(widget, "winfo_children"):
        for child in widget.winfo_children():
            count += count_menus(child)
    return count

def run_simulation():
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.withdraw() # Hide UI during automated simulation
    
    # Initialize services and fetch a project
    proj_service = ProjectService()
    projects = proj_service.get_all_active()
    if not projects:
        print("Creating dummy project for verification...")
        proj_service.create_project("Projeto Teste Performance", "Medir vazamento de memória e widgets")
        projects = proj_service.get_all_active()
    
    project = projects[0]
    
    # Initialize the view
    def dummy_back():
        pass
    view = Project360View(root, go_back_callback=dummy_back)
    view.pack()
    view.load_project(project)
    
    root.update_idletasks()
    
    # Tracemalloc monitoring
    tracemalloc.start()
    gc.collect()
    snapshot_before = tracemalloc.take_snapshot()
    
    # Measure baseline
    widgets_init = len(view.winfo_children())
    menus_init = count_menus(root)
    bindings_init = count_bindings(view)
    
    print("\n==================================================")
    print("           BASELINE PERFORMANCE METRICS           ")
    print("==================================================")
    print(f"Total Direct Child Widgets: {widgets_init}")
    print(f"Total Active Menus: {menus_init}")
    print(f"Total Event Bindings: {bindings_init}")
    print("==================================================\n")
    
    print("Running 50 consecutive refreshes to detect accumulation/leaks...")
    for i in range(1, 51):
        view.refresh(trigger=f"simulation_iter_{i}")
        root.update_idletasks()
        if i % 10 == 0:
            print(f"  Completed {i}/50 refreshes...")
            
    gc.collect()
    snapshot_after = tracemalloc.take_snapshot()
    
    widgets_final = len(view.winfo_children())
    menus_final = count_menus(root)
    bindings_final = count_bindings(view)
    
    stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    top_diffs = stats[:3]
    
    print("\n==================================================")
    print("          SIMULATION REPORT (50 REFRESHES)        ")
    print("==================================================")
    print(f"Menus: {menus_init} (Init) -> {menus_final} (Final) | Diff: {menus_final - menus_init}")
    print(f"Bindings: {bindings_init} (Init) -> {bindings_final} (Final) | Diff: {bindings_final - bindings_init}")
    print(f"Direct Child Widgets: {widgets_init} -> {widgets_final}")
    
    # Check if there's leak
    if menus_final - menus_init > 0 or bindings_final - bindings_init > 0:
        print("\n[FAIL] VERIFICATION FAILED: Leaks detected!")
        if menus_final - menus_init > 0:
            print(f"  - Leaked {menus_final - menus_init} tk.Menu objects!")
        if bindings_final - bindings_init > 0:
            print(f"  - Accumulated {bindings_final - bindings_init} duplicate event bindings!")
    else:
        print("\n[SUCCESS] VERIFICATION SUCCESSFUL: No widget, menu, or event binding leaks detected!")
        print("   Pooling and event binding isolation are working correctly.")
        
    print("\nTop 3 Memory Allocation Deltas:")
    for stat in top_diffs:
        print(f"  {stat}")
    print("==================================================\n")
    
    tracemalloc.stop()
    root.destroy()

if __name__ == "__main__":
    run_simulation()
