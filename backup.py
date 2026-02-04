import shutil
import os
from datetime import datetime
import schedule
import threading
import time

def create_backup():
    """Create a backup of all data files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'backups/backup_{timestamp}'
    
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    os.makedirs(backup_dir)
    
    # Backup all JSON files
    for filename in os.listdir('data'):
        if filename.endswith('.json'):
            shutil.copy2(
                os.path.join('data', filename),
                os.path.join(backup_dir, filename)
            )
    
    # Clean old backups (keep last 10)
    backups = sorted(os.listdir('backups'))
    if len(backups) > 10:
        for old_backup in backups[:-10]:
            shutil.rmtree(os.path.join('backups', old_backup))

def start_backup_scheduler():
    """Start the backup scheduler in a separate thread"""
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    # Create backup every day at midnight
    schedule.every().day.at("00:00").do(create_backup)
    
    # Run the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start() 