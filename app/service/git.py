import subprocess
import sys
import os
import shutil

def auto_update():
    """Mengecek integritas file dan update dari GitHub."""
    git_exists = shutil.which("git") is not None

    # Auto-install Git jika tidak ditemukan
    if not git_exists:
        if os.path.exists("/data/data/com.termux"):
            print("📦 Menginstal Git di Termux...")
            subprocess.run(["pkg", "install", "git", "-y"], capture_output=True)
            git_exists = True
        elif os.name == 'nt':
            print("📦 Menginstal Git di Windows...")
            subprocess.run(["winget", "install", "--id", "Git.Git", "-e", "--silent"], capture_output=True)
            git_exists = True

    if git_exists:
        try:
            print("🔍 Mengecek integritas file dan pembaruan...")
            # Ambil data terbaru dari GitHub
            subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True)
            
            # Deteksi file hilang atau perbedaan versi
            check_deleted = subprocess.check_output(["git", "ls-files", "--deleted"]).decode().strip()
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", "origin/main"]).decode().strip()
            
            if check_deleted or local_hash != remote_hash:
                if check_deleted:
                    print("⚠️ Terdeteksi file hilang/rusak. Memperbaiki sistem...")
                else:
                    print("🚀 Versi baru ditemukan! Mengupdate otomatis...")
                
                # Paksa sinkronisasi (Reset --hard memulihkan file hilang & update kode)
                subprocess.check_output(["git", "reset", "--hard", "origin/main"])
                print("✅ Sinkronisasi selesai. Menjalankan ulang aplikasi...")
                
                # RESTART APLIKASI
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("✅ Aplikasi sudah versi terbaru.")
        except Exception as e:
            print(f"ℹ️ Update dilewati: {e}")
    else:
        print("⚠️ Skip update otomatis karena Git tidak tersedia.")