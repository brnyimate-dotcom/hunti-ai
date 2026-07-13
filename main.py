import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import json
import datetime
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List

# Import database and email modules
from database import init_db, get_lead_count_from_db, log_form_submission
from email_sender import send_pitch_email
from browser_automation import fill_and_submit_form

# Import your existing modules
from vision import capture_screen
from brain import ask_assistant, build_pitches, get_pitches_from_db, log_email_sent
from actions import perform_action
from voice import speak_thought

# --- Configuration ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class HuntiUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        
        # Initialize the database immediately
        init_db()
        
        self.title("Hunti AI - Premium Edition")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # Variables
        self.volume_var = ctk.IntVar(value=100)
        self.speech_rate_var = ctk.IntVar(value=150)
        self.temperature_var = ctk.DoubleVar(value=0.2)
        self.auto_speak_var = ctk.BooleanVar(value=True)
        
        self.generated_pitches: List[Dict[str, Any]] = []
        
        # Logging setup
        log_file = Path(__file__).with_name("app_debug.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s: %(message)s",
        )
        logging.debug("HuntiUI initialized")

        self._build_ui()
        self._load_initial_stats()

    def _load_initial_stats(self) -> None:
        """Load initial stats from the database."""
        try:
            lead_count = get_lead_count_from_db()
            self.badge_leads.configure(text=f"Total Leads: {lead_count}")
        except Exception as e:
            print(f"Error loading stats: {e}")

    def _build_ui(self) -> None:
        # --- Header with Summary Badges ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header_frame, text="Hunti AI", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="Premium Edition", text_color="gray", font=ctk.CTkFont(size=12)).pack(side="left", pady=15)

        # Badges
        badge_frame = ctk.CTkFrame(self, corner_radius=10)
        badge_frame.pack(fill="x", padx=20, pady=10)
        
        self.badge_leads = ctk.CTkLabel(badge_frame, text="Total Leads: 0", font=ctk.CTkFont(size=14, weight="bold"))
        self.badge_leads.pack(side="left", padx=20, pady=15)
        
        self.badge_tasks = ctk.CTkLabel(badge_frame, text="Pending Tasks: 0", font=ctk.CTkFont(size=14, weight="bold"))
        self.badge_tasks.pack(side="left", padx=20, pady=15)
        
        self.badge_activity = ctk.CTkLabel(badge_frame, text="Last Activity: Never", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2196F3")
        self.badge_activity.pack(side="left", padx=20, pady=15)

        # --- Main Tab View ---
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.tab_assistant = self.tabview.add("Assistant")
        self.tab_pitches = self.tabview.add("Sales Pitches")
        self.tab_settings = self.tabview.add("Settings")

        self._build_assistant_tab(self.tab_assistant)
        self._build_pitches_tab(self.tab_pitches)
        self._build_settings_tab(self.tab_settings)

        # --- Status Bar ---
        self.status_label = ctk.CTkLabel(self, text="Status: Ready", text_color="gray", anchor="w")
        self.status_label.pack(fill="x", padx=20, pady=(0, 15))

    # --- Assistant Tab ---
    def _build_assistant_tab(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(parent, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        ctk.CTkLabel(left_panel, text="Task History", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=15, pady=(15, 5), anchor="w")
        self.task_history_box = ctk.CTkTextbox(left_panel, font=ctk.CTkFont(size=12), corner_radius=8)
        self.task_history_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        center_panel = ctk.CTkFrame(parent, fg_color="transparent")
        center_panel.grid(row=0, column=1, sticky="nsew")

        input_frame = ctk.CTkFrame(center_panel, corner_radius=10)
        input_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(input_frame, text="Hunti Task", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.task_entry = ctk.CTkEntry(input_frame, placeholder_text="Ask Hunti AI to do something...", height=40, font=ctk.CTkFont(size=14), corner_radius=8)
        self.task_entry.pack(fill="x", padx=15, pady=(0, 10))

        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))
        
        self.run_button = ctk.CTkButton(btn_row, text="Run Task", height=35, command=self.on_run_task)
        self.run_button.pack(side="left")
        
        ctk.CTkButton(btn_row, text="Clear", height=35, fg_color="gray40", hover_color="gray30", command=self._clear_output).pack(side="left", padx=10)
        
        self.auto_speak_cb = ctk.CTkCheckBox(btn_row, text="Auto speak responses", variable=self.auto_speak_var)
        self.auto_speak_cb.pack(side="right")

        output_frame = ctk.CTkFrame(center_panel, corner_radius=10)
        output_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(output_frame, text="Assistant Output", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        self.output_text = ctk.CTkTextbox(output_frame, font=ctk.CTkFont(size=13, family="Consolas"), corner_radius=8, wrap="word")
        self.output_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.output_text.configure(state="disabled")

        right_panel = ctk.CTkFrame(parent, corner_radius=10)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0), pady=0)
        
        ctk.CTkLabel(right_panel, text="Agent Status", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=15, pady=(15, 5), anchor="w")
        self.agent_status_label = ctk.CTkLabel(right_panel, text="Ready to receive a task.", font=ctk.CTkFont(size=12), justify="left")
        self.agent_status_label.pack(fill="x", padx=15, pady=10)

    # --- Pitches Tab ---
    def _build_pitches_tab(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(parent, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        ctk.CTkLabel(left_panel, text="Lead Source", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(left_panel, text="Database: hunti.db", text_color="gray").pack(anchor="w", padx=15, pady=5)

        self.generate_btn = ctk.CTkButton(left_panel, text="Generate Sales Pitches", height=40, command=self._generate_pitches)
        self.generate_btn.pack(fill="x", padx=15, pady=10)
        
        self.pitch_status_label = ctk.CTkLabel(left_panel, text="Ready to build pitches.", text_color="gray")
        self.pitch_status_label.pack(padx=15, pady=(0, 10))

        ctk.CTkLabel(left_panel, text="Generated Pitches", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.pitch_list_frame = ctk.CTkScrollableFrame(left_panel, corner_radius=8)
        self.pitch_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        right_panel = ctk.CTkFrame(parent, corner_radius=10)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        
        ctk.CTkLabel(right_panel, text="Selected Pitch", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        self.pitch_details = ctk.CTkTextbox(right_panel, font=ctk.CTkFont(size=13, family="Consolas"), corner_radius=8, wrap="word")
        self.pitch_details.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.send_email_btn = ctk.CTkButton(right_panel, text="Send via Email", command=self._send_pitch_email)
        self.send_email_btn.pack(padx=15, pady=(0, 5), anchor="e")
        
        self.submit_web_btn = ctk.CTkButton(right_panel, text="Submit via Website", fg_color="gray40", hover_color="gray30", command=self._submit_via_website)
        self.submit_web_btn.pack(padx=15, pady=(0, 5), anchor="e")
        
        ctk.CTkButton(right_panel, text="Copy Selected Pitch", fg_color="gray40", hover_color="gray30", command=self._copy_selected_pitch).pack(padx=15, pady=(0, 15), anchor="e")

    # --- Settings Tab ---
    def _build_settings_tab(self, parent) -> None:
        settings_frame = ctk.CTkFrame(parent, corner_radius=10)
        settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(settings_frame, text="Audio Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))

        self._create_slider(settings_frame, "Volume", self.volume_var, 0, 100)
        self._create_slider(settings_frame, "Speech rate", self.speech_rate_var, 80, 300)
        self._create_slider(settings_frame, "AI temperature", self.temperature_var, 0.0, 1.0)

        ctk.CTkButton(settings_frame, text="Test TTS", fg_color="gray40", hover_color="gray30", command=self._on_test_tts).pack(pady=(20, 0), anchor="w", padx=20)

    def _create_slider(self, parent, label, variable, min_val, max_val) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(frame, text=f"{label}: {int(variable.get())}", width=150, anchor="w").pack(side="left")
        slider = ctk.CTkSlider(frame, from_=min_val, to=max_val, variable=variable, command=lambda v: self._update_slider_label(frame, label, variable))
        slider.pack(side="left", fill="x", expand=True, padx=10)

    def _update_slider_label(self, frame, label, variable):
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=f"{label}: {int(variable.get())}")
                break

    # --- Logic Functions ---

    def on_run_task(self) -> None:
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning("Hunti AI", "Enter a task before running.")
            return

        self.run_button.configure(state="disabled", text="Thinking...")
        self._append_output(f"> {task}\n")
        self._set_status("Capturing screen and querying AI...")

        thread = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
        thread.start()

    def _execute_task(self, task: str) -> None:
        try:
            _, image_b64 = capture_screen()
            result = ask_assistant(task, image_b64, temperature=self.temperature_var.get())

            self._append_output(f"{json.dumps(result, indent=2)}\n\n")
            self._set_status("Awaiting confirmation...")
            
            if not self._confirm_action(result):
                self._append_output("Action canceled by user.\n\n")
                self._set_status("Canceled.")
                return

            thought = result.get("thought", "")
            action_status = perform_action(result)
            self._append_output(f"Action result: {json.dumps(action_status)}\n\n")
            self._set_status("Action executed.")

            if self.auto_speak_var.get() and thought:
                speak_thought(thought, rate=self.speech_rate_var.get(), volume=(self.volume_var.get() / 100.0))

            text_to_speak = result.get("text", "")
            if text_to_speak and text_to_speak != thought:
                speak_thought(text_to_speak, rate=self.speech_rate_var.get(), volume=(self.volume_var.get() / 100.0))

            self.after(0, lambda: self._add_task_history(task))
            
        except Exception as exc:
            self._append_output(f"Error: {exc}\n\n")
            self._set_status("Failed.")
            self.after(0, lambda msg=str(exc): messagebox.showerror("Task Failed", f"Could not complete task:\n\n{msg}"))
        finally:
            self.run_button.configure(state="normal", text="Run Task")

    def _confirm_action(self, action_payload: dict) -> bool:
        result_event = threading.Event()
        user_response = {"confirmed": False}

        def ask_user() -> None:
            action_text = json.dumps(action_payload, indent=2)
            user_response["confirmed"] = messagebox.askyesno("Confirm Action", f"Hunti AI wants to execute:\n\n{action_text}\n\nProceed?")
            result_event.set()

        self.after(0, ask_user)
        result_event.wait()
        return user_response["confirmed"]

    def _append_output(self, text: str) -> None:
        def callback() -> None:
            self.output_text.configure(state="normal")
            self.output_text.insert("end", text)
            self.output_text.see("end")
            self.output_text.configure(state="disabled")
        self.after(0, callback)

    def _set_status(self, message: str) -> None:
        def callback() -> None:
            self.status_label.configure(text=f"Status: {message}")
            self.badge_activity.configure(text=f"Last Activity: {datetime.datetime.now().strftime('%H:%M')}")
        self.after(0, callback)

    def _add_task_history(self, task: str) -> None:
        self.task_history_box.insert("end", f"{task}\n")
        self.badge_tasks.configure(text=f"Pending Tasks: {self.task_history_box.get('1.0', 'end').count(chr(10)) - 1}")

    def _clear_output(self) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _generate_pitches(self) -> None:
        self.generate_btn.configure(state="disabled", text="Generating...")
        self.pitch_status_label.configure(text="Generating pitches...")
        thread = threading.Thread(target=self._generate_pitches_worker, daemon=True)
        thread.start()

    def _generate_pitches_worker(self) -> None:
        try:
            pitches = build_pitches() 
            
            db_pitches = get_pitches_from_db()
            self.after(0, lambda: self._populate_pitch_list(db_pitches))
            self.after(0, lambda: self.pitch_status_label.configure(text=f"Created {len(pitches)} pitches."))
            
            self.after(0, lambda: self.badge_leads.configure(text=f"Total Leads: {get_lead_count_from_db()}"))
            
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Error", f"Could not generate pitches: {exc}"))
        finally:
            self.after(0, lambda: self.generate_btn.configure(state="normal", text="Generate Sales Pitches"))

    def _populate_pitch_list(self, pitches: List[Dict[str, Any]]) -> None:
        self.generated_pitches = pitches
        for widget in self.pitch_list_frame.winfo_children():
            widget.destroy()
            
        self.pitch_details.delete("1.0", "end")

        for idx, item in enumerate(pitches):
            btn = ctk.CTkButton(
                self.pitch_list_frame, 
                text=f"{item['company_name']}", 
                anchor="w", 
                height=40,
                command=lambda i=idx: self._show_pitch_details(i)
            )
            btn.pack(fill="x", pady=5)

    def _show_pitch_details(self, index: int) -> None:
        pitch_item = self.generated_pitches[index]
        self.pitch_details.delete("1.0", "end")
        self.pitch_details.insert("1.0", f"Company: {pitch_item['company_name']}\n\n{pitch_item['pitch_text']}")

    def _copy_selected_pitch(self) -> None:
        pitch_text = self.pitch_details.get("1.0", "end").strip()
        if not pitch_text:
            messagebox.showwarning("Copy", "No pitch selected.")
            return
        self.clipboard_clear()
        self.clipboard_append(pitch_text)
        self._set_status("Pitch copied to clipboard.")

    def _send_pitch_email(self) -> None:
        pitch_text = self.pitch_details.get("1.0", "end").strip()
        if not pitch_text or "Company:" not in pitch_text:
            messagebox.showwarning("No Pitch Selected", "Please select a pitch from the list first.")
            return

        company_name = pitch_text.split("\n")[0].replace("Company: ", "")
        
        selected_pitch_obj = None
        for p in self.generated_pitches:
            if p['company_name'] == company_name:
                selected_pitch_obj = p
                break

        recipient_email = ctk.CTkInputDialog(
            text=f"Enter the email address for {company_name}:",
            title="Send Pitch"
        ).get_input()

        if not recipient_email or "@" not in recipient_email:
            return

        self.send_email_btn.configure(state="disabled", text="Sending...")
        
        try:
            subject = f"AI Automation Proposal for {company_name}"
            result = send_pitch_email(recipient_email, subject, pitch_text)
            
            if selected_pitch_obj and 'id' in selected_pitch_obj:
                log_email_sent(selected_pitch_obj['id'], recipient_email, subject)
                
            messagebox.showinfo("Success", result)
        except Exception as e:
            messagebox.showerror("Email Failed", str(e))
        finally:
            self.send_email_btn.configure(state="normal", text="Send via Email")

    def _submit_via_website(self) -> None:
        """Handles submitting the selected pitch via a website contact form."""
        pitch_text = self.pitch_details.get("1.0", "end").strip()
        if not pitch_text or "Company:" not in pitch_text:
            messagebox.showwarning("No Pitch Selected", "Please select a pitch from the list first.")
            return

        company_name = pitch_text.split("\n")[0].replace("Company: ", "")
        
        # Find the currently selected pitch object to get its DB ID for logging
        selected_pitch_obj = None
        for p in self.generated_pitches:
            if p['company_name'] == company_name:
                selected_pitch_obj = p
                break

        # 1. Ask for the website URL
        target_url = ctk.CTkInputDialog(
            text=f"Enter the contact page URL for {company_name}:",
            title="Submit via Website"
        ).get_input()

        if not target_url or not target_url.startswith("http"):
            return

        # 2. Ask for sender info
        sender_name = ctk.CTkInputDialog(text="Enter your name:", title="Sender Info").get_input()
        sender_email = ctk.CTkInputDialog(text="Enter your email:", title="Sender Info").get_input()

        if not sender_name or not sender_email:
            return

        # 3. Update UI and run in background thread
        self.submit_web_btn.configure(state="disabled", text="Submitting...")

        def run_automation():
            try:
                data = {
                    "name": sender_name,
                    "email": sender_email,
                    "message": pitch_text
                }
                # Run async function in a new event loop for the thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(fill_and_submit_form(target_url, data, headless=True))
                loop.close()

                if success:
                    # Log to database!
                    if selected_pitch_obj and 'id' in selected_pitch_obj:
                        log_form_submission(selected_pitch_obj['id'], company_name, target_url)
                    
                    self.after(0, lambda: messagebox.showinfo("Success", f"Form submitted to {target_url}!"))
                else:
                    self.after(0, lambda: messagebox.showerror("Failed", "Could not submit the form. Check logs."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self.submit_web_btn.configure(state="normal", text="Submit via Website"))

        thread = threading.Thread(target=run_automation, daemon=True)
        thread.start()

    def _on_test_tts(self) -> None:
        speak_thought("This is a volume test from Hunti AI.", rate=self.speech_rate_var.get(), volume=(self.volume_var.get() / 100.0))


if __name__ == "__main__":
    app = HuntiUI()
    app.mainloop()