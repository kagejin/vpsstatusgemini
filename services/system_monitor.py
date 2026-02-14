import subprocess
import logging

logger = logging.getLogger(__name__)

def ping_host(host: str) -> str:
    """
    Pings a host and returns the result message.
    """
    try:
        # -c 1: send 1 packet
        # -W 2: wait up to 2 seconds
        command = ['ping', '-c', '1', '-W', '2', host]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            return f"✅ Ping to {host} successful!\n{result.stdout.splitlines()[-1]}"
        else:
            return f"❌ Ping to {host} failed."
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return f"⚠️ Error executing ping command: {e}"

def check_service_status(service_name: str) -> bool:
    """
    Checks if a systemd service is active.
    """
    try:
        command = ['systemctl', 'is-active', service_name]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 'active' is the standard output for a running service
        return result.stdout.strip() == 'active'
    except Exception as e:
        logger.error(f"Error checking service {service_name}: {e}")
        return False

def get_system_stats() -> str:
    """
    Returns a formatted string of system stats (CPU, RAM).
    """
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        
        return (
            f"💻 **System Stats**:\n"
            f"CPU: {cpu_usage}%\n"
            f"RAM: {ram.percent}% ({ram.used // (1024*1024)}MB / {ram.total // (1024*1024)}MB)"
        )
    except ImportError:
        return "psutil not installed, cannot retrieve stats."
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return f"Error getting stats: {e}"
