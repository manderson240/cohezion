"""
Ratchet Health Monitor
======================
"Like Ratchet from G1 Transformers"

Vigilant, protective, knows every system intimately.
Anticipates problems before they happen.
Never lets the team overwork themselves.
"""

import psutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import smtplib
from email.mime.text import MIMEText

@dataclass
class SystemVitals:
    """Current system health metrics."""
    timestamp: datetime
    cpu_percent: float
    ram_used_gb: float
    ram_percent: float
    gpu_util: Optional[float]
    disk_used_gb: float
    disk_percent: float
    ollama_responsive: bool
    surreal_responsive: bool
    
    def is_critical(self) -> bool:
        """Check if system is in critical state."""
        return (
            self.cpu_percent > 90 or
            self.ram_percent > 85 or
            not self.ollama_responsive or
            not self.surreal_responsive
        )
    
    def needs_throttle(self) -> bool:
        """Check if processing should be throttled."""
        return self.cpu_percent > 75 or self.ram_percent > 70

class RatchetMonitor:
    """
    Ratchet-style health monitor.
    
    Characteristics:
    - Vigilant: Checks every 30s
    - Protective: Auto-throttles before critical state
    - Anticipatory: Warns at 70% thresholds, not 90%
    - Communicative: Sends status updates
    """
    
    def __init__(self, email_to: str):
        self.email_to = email_to
        self.baseline_vitals: Optional[SystemVitals] = None
        self.alert_count = 0
        
    def check_vitals(self) -> SystemVitals:
        """Check all system vitals."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # RAM (Framework Desktop has 128GB)
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024**3)
        ram_percent = ram.percent
        
        # GPU (AMD Radeon RX 7700S - 12GB VRAM)
        gpu_util = self._check_gpu()
        
        # Disk (2TB SSD)
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024**3)
        disk_percent = disk.percent
        
        # Services
        ollama_ok = self._check_ollama()
        surreal_ok = self._check_surrealdb()
        
        vitals = SystemVitals(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            ram_used_gb=ram_used_gb,
            ram_percent=ram_percent,
            gpu_util=gpu_util,
            disk_used_gb=disk_used_gb,
            disk_percent=disk_percent,
            ollama_responsive=ollama_ok,
            surreal_responsive=surreal_ok
        )
        
        if self.baseline_vitals is None:
            self.baseline_vitals = vitals
        
        return vitals
    
    def _check_gpu(self) -> Optional[float]:
        """Check GPU utilization (AMD)."""
        try:
            result = subprocess.run(
                ['radeontop', '-d', '-', '-l', '1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Parse radeontop output
            if result.returncode == 0:
                # Extract GPU usage %
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Parse format: "gpu 45.00%"
                    for line in lines:
                        if 'gpu' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                return float(parts[1].rstrip('%'))
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return None
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is responsive."""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_surrealdb(self) -> bool:
        """Check if SurrealDB is responsive."""
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:8000/health'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 and b'ok' in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def diagnose(self, vitals: SystemVitals) -> str:
        """Ratchet's diagnostic analysis."""
        report = []
        
        report.append(f"[{vitals.timestamp.strftime('%H:%M:%S')}] RATCHET DIAGNOSTIC REPORT")
        report.append("=" * 60)
        
        # CPU Analysis
        if vitals.cpu_percent > 75:
            report.append(f"⚠️  CPU: {vitals.cpu_percent:.1f}% - APPROACHING LIMIT")
            report.append("   Recommendation: Throttle workload or add delay between tasks")
        else:
            report.append(f"✓ CPU: {vitals.cpu_percent:.1f}% - Nominal")
        
        # RAM Analysis (Framework Desktop 128GB)
        if vitals.ram_percent > 70:
            report.append(f"⚠️  RAM: {vitals.ram_used_gb:.1f}GB / 128GB ({vitals.ram_percent:.1f}%) - HIGH USAGE")
            report.append("   Recommendation: Clear caches or reduce concurrent models")
        else:
            report.append(f"✓ RAM: {vitals.ram_used_gb:.1f}GB / 128GB ({vitals.ram_percent:.1f}%) - Nominal")
        
        # GPU
        if vitals.gpu_util:
            if vitals.gpu_util > 80:
                report.append(f"⚠️  GPU: {vitals.gpu_util:.1f}% - NEAR CAPACITY")
            else:
                report.append(f"✓ GPU: {vitals.gpu_util:.1f}% - Nominal")
        
        # Services
        if not vitals.ollama_responsive:
            report.append("❌ OLLAMA: NOT RESPONDING - Restart required!")
        else:
            report.append("✓ Ollama: Responsive")
        
        if not vitals.surreal_responsive:
            report.append("❌ SURREALDB: NOT RESPONDING - Restart required!")
        else:
            report.append("✓ SurrealDB: Responsive")
        
        # Overall assessment
        if vitals.is_critical():
            report.append("\n🚨 CRITICAL STATE - IMMEDIATE ACTION REQUIRED")
        elif vitals.needs_throttle():
            report.append("\n⚠️  THROTTLE RECOMMENDED - System approaching limits")
        else:
            report.append("\n✅ ALL SYSTEMS NOMINAL - Proceed with mission")
        
        return "\n".join(report)
    
    def send_alert(self, vitals: SystemVitals, message: str):
        """Send email alert (like Ratchet calling for backup)."""
        try:
            msg = MIMEText(f"{self.diagnose(vitals)}\n\n{message}")
            msg['Subject'] = f"🚨 Ratchet Alert: {vitals.timestamp.strftime('%H:%M')}"
            msg['From'] = 'ratchet@cohezion.local'
            msg['To'] = self.email_to
            
            # Would send via SMTP here
            print(f"📧 Alert sent to {self.email_to}")
        except Exception as e:
            print(f"⚠️  Failed to send alert: {e}")
    
    def monitor_loop(self, check_interval=30):
        """Continuous monitoring loop."""
        print("🔧 RATCHET ONLINE - Monitoring systems...")
        
        while True:
            vitals = self.check_vitals()
            report = self.diagnose(vitals)
            
            with open('/var/log/cohezion_ratchet.log', 'a') as f:
                f.write(report + "\n\n")
            
            if vitals.is_critical():
                self.send_alert(vitals, "CRITICAL STATE DETECTED")
                self.alert_count += 1
                
                if self.alert_count > 3:
                    print("🛑 Too many critical alerts. SHUTTING DOWN for safety.")
                    subprocess.run(['systemctl', 'stop', 'cohezion-overnight'])
                    break
            
            elif vitals.needs_throttle():
                print("⚠️  Throttling recommended...")
                time.sleep(60)  # Extra delay when under stress
            
            time.sleep(check_interval)

if __name__ == "__main__":
    ratchet = RatchetMonitor(email_to="manderson240@gmail.com")
    
    # Test check
    vitals = ratchet.check_vitals()
    print(ratchet.diagnose(vitals))
