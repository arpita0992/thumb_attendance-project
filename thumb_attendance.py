"""
Gesture Attendance System - VS Code Only (FIXED)
- Same face = Same EMP ID
- One entry per session
- No hanging
PALM = IN | THUMB = OUT | 4 Hour Time Limit
"""

import cv2
import numpy as np
import datetime
import json
import os
import threading
import time
import sys
from PIL import Image
import mediapipe as mp

print("=" * 60)
print("🎯 GESTURE ATTENDANCE SYSTEM - VS CODE VERSION")
print("=" * 60)

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

class AttendanceSystem:
    def __init__(self):
        self.attendance_file = "attendance_records.json"
        self.attendance_log = self.load_data()
        self.time_limit_hours = 4
        self.is_running = False
        self.cap = None
        self.hands = None
        self.running = True
        self.current_user_id = None  # Store current user ID
        self.user_counter = 1
        self.last_action_time = {}
        self.cooldown = 3  # seconds between actions
        self.session_active = False  # Track if session is active
        
        # Initialize hands
        try:
            self.hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            print("✅ MediaPipe initialized")
        except Exception as e:
            print(f"❌ Error: {e}")
            return
        
        print(f"✅ Time limit: {self.time_limit_hours} hours")
        print("=" * 60)
        self.show_menu()
    
    def load_data(self):
        if os.path.exists(self.attendance_file):
            try:
                with open(self.attendance_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_data(self):
        try:
            with open(self.attendance_file, 'w') as f:
                json.dump(self.attendance_log, f, indent=2)
        except:
            pass
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu(self):
        while self.running:
            self.clear_screen()
            print("=" * 60)
            print("🎯 GESTURE ATTENDANCE SYSTEM")
            print("=" * 60)
            
            # Show current session status
            if self.session_active:
                print(f"\n🟢 SESSION ACTIVE - User: {self.current_user_id}")
                print("   Press 'q' in camera window to stop")
            else:
                print("\n⚪ No active session")
            
            print("\n📋 MENU:")
            print("1. ▶ START CAMERA (Mark Attendance)")
            print("2. 📊 VIEW ATTENDANCE")
            print("3. ⏱️ CHANGE TIME LIMIT (Current: {} hours)".format(self.time_limit_hours))
            print("4. 🗑️ DELETE ALL RECORDS")
            print("5. ❌ EXIT")
            print("\n" + "=" * 60)
            
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                self.start_camera()
            elif choice == "2":
                self.view_attendance()
            elif choice == "3":
                self.change_time_limit()
            elif choice == "4":
                self.delete_records()
            elif choice == "5":
                self.running = False
                print("\n👋 Goodbye!")
                sys.exit(0)
            else:
                print("\n❌ Invalid choice! Press Enter to continue...")
                input()
    
    def get_user_id(self):
        """Get or create a consistent user ID"""
        # If we already have a user ID for this session, use it
        if self.current_user_id:
            return self.current_user_id
        
        # Check if there are existing records
        if self.attendance_log:
            # Get the last user ID and increment
            existing_ids = [int(id.replace('EMP_', '')) for id in self.attendance_log.keys() if id.startswith('EMP_')]
            if existing_ids:
                next_id = max(existing_ids) + 1
            else:
                next_id = 1
        else:
            next_id = 1
        
        self.current_user_id = f"EMP_{next_id}"
        return self.current_user_id
    
    def start_camera(self):
        """Start camera for attendance"""
        if self.is_running:
            print("Camera already running!")
            input("Press Enter to continue...")
            return
        
        # Reset session
        self.current_user_id = self.get_user_id()
        self.session_active = True
        self.last_action_time = {}
        
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("❌ Camera not found!")
                self.session_active = False
                input("Press Enter to continue...")
                return
            
            print("✅ Camera opened!")
            print(f"\n📌 USER ID: {self.current_user_id}")
            print("📌 HOW TO USE:")
            print("   🖐️ Show PALM (open hand) = Mark IN")
            print("   👍 Show THUMB (fist) = Mark OUT")
            print("   Press 'q' or 'ESC' to stop camera")
            print("\n⏳ Starting camera in 2 seconds...")
            time.sleep(2)
            
            self.is_running = True
            self.process_video()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.session_active = False
            input("Press Enter to continue...")
    
    def process_video(self):
        """Process video frames"""
        frame_count = 0
        last_gesture_time = 0
        gesture_cooldown = 2  # seconds between gestures
        current_gesture = None
        gesture_stable_count = 0
        required_stable_frames = 10  # frames needed for stable detection
        
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb)
                
                # Display info on frame
                cv2.putText(frame, f"USER: {self.current_user_id}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "PALM = IN | THUMB = OUT", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "Press 'q' to stop", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Check if user is already IN
                if self.current_user_id in self.attendance_log:
                    status = self.attendance_log[self.current_user_id].get('last_action', 'N/A')
                    cv2.putText(frame, f"Status: {status}", (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if status == 'IN' else (0, 0, 255), 2)
                
                if results.multi_hand_landmarks:
                    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        # Draw landmarks
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                            mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
                        )
                        
                        hand_type = handedness.classification[0].label
                        total, is_palm, only_thumb = self.count_fingers(hand_landmarks.landmark, hand_type)
                        
                        # Detect gesture with stability check
                        detected_gesture = None
                        
                        if is_palm and total == 5:
                            detected_gesture = "IN"
                            cv2.putText(frame, "🖐️ PALM DETECTED", (10, 170), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                            cv2.rectangle(frame, (10, 200), (300, 240), (0, 255, 0), -1)
                            cv2.putText(frame, "CHECK-IN", (20, 230), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                        
                        elif only_thumb:
                            detected_gesture = "OUT"
                            cv2.putText(frame, "👍 THUMB DETECTED", (10, 170), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                            cv2.rectangle(frame, (10, 200), (310, 240), (0, 0, 255), -1)
                            cv2.putText(frame, "CHECK-OUT", (20, 230), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        else:
                            cv2.putText(frame, f"Fingers: {total}", (10, 170), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                            cv2.putText(frame, f"Hand: {hand_type}", (10, 200), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # Stable gesture detection
                        if detected_gesture:
                            if detected_gesture == current_gesture:
                                gesture_stable_count += 1
                            else:
                                current_gesture = detected_gesture
                                gesture_stable_count = 1
                            
                            # If gesture is stable for required frames
                            if gesture_stable_count >= required_stable_frames:
                                current_time = time.time()
                                if current_time - last_gesture_time > gesture_cooldown:
                                    last_gesture_time = current_time
                                    if detected_gesture == "IN":
                                        self.mark_attendance(self.current_user_id, "IN")
                                    elif detected_gesture == "OUT":
                                        self.mark_attendance(self.current_user_id, "OUT")
                                    gesture_stable_count = 0
                                    current_gesture = None
                        else:
                            # Reset stability if no gesture detected
                            if gesture_stable_count > 0:
                                gesture_stable_count = max(0, gesture_stable_count - 1)
                
                # Show frame
                cv2.imshow("Attendance System - VS Code", frame)
                
                # Check for quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # q or ESC
                    break
                
                frame_count += 1
                
            except Exception as e:
                print(f"Video error: {e}")
                break
        
        self.stop_camera()
    
    def stop_camera(self):
        """Stop camera"""
        self.is_running = False
        self.session_active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
        print("\n✅ Camera stopped")
        print(f"📌 User ID: {self.current_user_id}")
        input("Press Enter to continue...")
    
    def count_fingers(self, landmarks, handedness):
        """Count extended fingers"""
        if not landmarks:
            return 0, False, False
        
        # Thumb
        thumb_tip_x = landmarks[4].x
        thumb_ip_x = landmarks[3].x
        
        if handedness == "Right":
            thumb_extended = thumb_tip_x > thumb_ip_x
        else:
            thumb_extended = thumb_tip_x < thumb_ip_x
        
        # Other fingers
        fingers = []
        for i in [8, 12, 16, 20]:
            if landmarks[i].y < landmarks[i-2].y:
                fingers.append(True)
            else:
                fingers.append(False)
        
        total = sum(fingers) + (1 if thumb_extended else 0)
        is_palm = all(fingers) and thumb_extended
        only_thumb = thumb_extended and not any(fingers)
        
        return total, is_palm, only_thumb
    
    def is_within_time_limit(self, user_id):
        if user_id not in self.attendance_log:
            return False
        
        in_time = self.attendance_log[user_id].get('in_time')
        if not in_time:
            return False
        
        in_dt = datetime.datetime.fromisoformat(in_time)
        diff = (datetime.datetime.now() - in_dt).total_seconds() / 3600
        return diff < self.time_limit_hours
    
    def mark_attendance(self, user_id, action):
        """Mark attendance with cooldown"""
        now = datetime.datetime.now().isoformat()
        
        if user_id not in self.attendance_log:
            self.attendance_log[user_id] = {
                'in_time': None,
                'out_time': None,
                'last_action': None,
                'total_hours': 0,
                'entries': []
            }
        
        if action == "IN":
            if self.attendance_log[user_id]['in_time'] is None:
                self.attendance_log[user_id]['in_time'] = now
                self.attendance_log[user_id]['last_action'] = 'IN'
                if 'entries' not in self.attendance_log[user_id]:
                    self.attendance_log[user_id]['entries'] = []
                self.attendance_log[user_id]['entries'].append({
                    'action': 'IN',
                    'time': now
                })
                self.save_data()
                print(f"\n✅ {user_id} IN at {datetime.datetime.now().strftime('%H:%M:%S')}")
                self.view_attendance()
                return True
            else:
                print(f"\n⏳ {user_id} already IN")
                return False
        
        elif action == "OUT":
            if self.attendance_log[user_id]['in_time'] is None:
                print(f"\n⏳ {user_id} not checked IN yet")
                return False
            
            if not self.is_within_time_limit(user_id):
                in_time = datetime.datetime.fromisoformat(self.attendance_log[user_id]['in_time'])
                hours = (datetime.datetime.now() - in_time).total_seconds() / 3600
                
                self.attendance_log[user_id]['out_time'] = now
                self.attendance_log[user_id]['last_action'] = 'OUT'
                self.attendance_log[user_id]['total_hours'] = round(hours, 2)
                if 'entries' not in self.attendance_log[user_id]:
                    self.attendance_log[user_id]['entries'] = []
                self.attendance_log[user_id]['entries'].append({
                    'action': 'OUT',
                    'time': now,
                    'hours_worked': round(hours, 2)
                })
                self.save_data()
                print(f"\n✅ {user_id} OUT after {hours:.1f} hours")
                self.view_attendance()
                return True
            else:
                remaining = self.time_limit_hours - self.get_hours_since_in(user_id)
                print(f"\n⏳ Wait {remaining:.1f} hours for OUT")
                return False
        
        return False
    
    def get_hours_since_in(self, user_id):
        if user_id not in self.attendance_log:
            return 0
        
        in_time = self.attendance_log[user_id].get('in_time')
        if not in_time:
            return 0
        
        in_dt = datetime.datetime.fromisoformat(in_time)
        return (datetime.datetime.now() - in_dt).total_seconds() / 3600
    
    def view_attendance(self):
        """View attendance records"""
        self.clear_screen()
        print("=" * 60)
        print("📊 ATTENDANCE RECORDS")
        print("=" * 60)
        
        if not self.attendance_log:
            print("\n📭 No records found")
        else:
            print(f"\n{'ID':<15} {'Status':<12} {'IN Time':<20} {'Hours':<12} {'Entries':<8}")
            print("-" * 70)
            
            for user_id in sorted(self.attendance_log.keys()):
                data = self.attendance_log[user_id]
                status = data.get('last_action', 'N/A')
                in_time = data.get('in_time', '')
                hours = data.get('total_hours', 0)
                entries = data.get('entries', [])
                
                if in_time:
                    time_str = datetime.datetime.fromisoformat(in_time).strftime('%H:%M:%S')
                else:
                    time_str = '--:--:--'
                
                status_display = "🟢 IN" if status == 'IN' else "🔴 OUT" if status == 'OUT' else "⚪ N/A"
                hours_str = f"{hours:.1f}h" if hours > 0 else "--"
                entries_count = len(entries)
                
                print(f"{user_id:<15} {status_display:<12} {time_str:<20} {hours_str:<12} {entries_count:<8}")
                
                # Show entry history
                if entries:
                    print(f"  └─ History:")
                    for entry in entries[-3:]:  # Show last 3 entries
                        action = entry.get('action', '')
                        entry_time = entry.get('time', '')
                        if entry_time:
                            et = datetime.datetime.fromisoformat(entry_time).strftime('%H:%M:%S')
                            hours_worked = entry.get('hours_worked', '')
                            if hours_worked:
                                print(f"     {action}: {et} ({hours_worked:.1f}h)")
                            else:
                                print(f"     {action}: {et}")
            
            print("\n" + "=" * 60)
            total_records = len(self.attendance_log)
            print(f"Total Records: {total_records}")
        
        print("\n" + "=" * 60)
        input("\nPress Enter to continue...")
    
    def change_time_limit(self):
        """Change time limit"""
        self.clear_screen()
        print("=" * 60)
        print("⏱️ CHANGE TIME LIMIT")
        print("=" * 60)
        print(f"\nCurrent time limit: {self.time_limit_hours} hours")
        
        try:
            new_limit = input("\nEnter new time limit in hours: ").strip()
            if new_limit:
                hours = float(new_limit)
                if hours > 0:
                    self.time_limit_hours = hours
                    print(f"\n✅ Time limit set to {hours} hours")
                else:
                    print("\n❌ Please enter a positive number")
            else:
                print("\n❌ Invalid input")
        except:
            print("\n❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def delete_records(self):
        """Delete all records"""
        self.clear_screen()
        print("=" * 60)
        print("🗑️ DELETE ALL RECORDS")
        print("=" * 60)
        
        if not self.attendance_log:
            print("\n📭 No records to delete")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n⚠️ WARNING: This will delete {len(self.attendance_log)} record(s)")
        confirm = input("\nAre you sure? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            self.attendance_log = {}
            self.save_data()
            self.current_user_id = None
            self.user_counter = 1
            print("\n✅ All records deleted successfully!")
        else:
            print("\n❌ Operation cancelled")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        app = AttendanceSystem()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")