import os
import tempfile
import argparse
import requests
from typing import Optional
import json
try:
    import imageio_ffmpeg  # type: ignore
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe() or 'ffmpeg'
except Exception:
    FFMPEG_EXE = 'ffmpeg'

"""
YouTube/playlist ingest aracı

Gereksinimler:
  pip install yt-dlp requests

Kullanım örnekleri:
  python3 youtube_ingest.py --url https://youtu.be/XXXX --api http://localhost:8000
  python3 youtube_ingest.py --url https://www.youtube.com/playlist?list=YYYY --api http://localhost:8000

Notlar:
  - Sadece ses indirilir (m4a), geçici dosya olarak tutulur ve /ingest/video'a POST edilir
  - Her video için title ve url otomatik doldurulur, clean=true ile normalizasyon uygulanır
"""


def ingest_file(api_base: str, file_path: str, title: str, url: str, video_id: str, language: str = "tr", dry_run: bool = False) -> Optional[dict]:
    """Dosyayı FastAPI /ingest/video'a yükler ve JSON döndürür.
    dry_run=True → sadece önizleme, FAISS'e eklemez
    """
    endpoint = f"{api_base.rstrip('/')}/ingest/video"
    try:
        with open(file_path, 'rb') as f:
            files = { 'file': (os.path.basename(file_path), f, 'audio/m4a') }
            data = {
                'language': language,
                'title': title,
                'url': url,
                'video_id': video_id,
                'author': 'YouTube',
                'clean': 'true',
                'dry_run': 'true' if dry_run else 'false'
            }
            resp = requests.post(endpoint, files=files, data=data, timeout=600)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"❌ API yükleme hatası: {title} → {e}")
        return None
def load_ingested_registry(reg_path: str) -> set:
    if not os.path.exists(reg_path):
        return set()
    try:
        with open(reg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('video_ids', []))
    except Exception:
        return set()

def save_ingested_registry(reg_path: str, ids: set) -> None:
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, 'w', encoding='utf-8') as f:
        json.dump({'video_ids': sorted(list(ids))}, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="YouTube/Playlist ingest aracı")
    parser.add_argument('--url', required=True, help='YouTube video veya playlist URL')
    parser.add_argument('--api', default='http://localhost:8000', help='FastAPI base URL')
    parser.add_argument('--language', default='tr', help='Dil (whisper)')
    parser.add_argument('--review', action='store_true', help='FAISS eklemeden önce içerik önizle ve onay iste')
    parser.add_argument('--show-full', action='store_true', help='Önizlemede temiz metnin tamamını terminalde göster')
    args = parser.parse_args()

    try:
        import yt_dlp  # type: ignore
    except ImportError:
        raise SystemExit("yt-dlp eksik. Kurun: pip install yt-dlp")

    ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'outtmpl': os.path.join(tempfile.gettempdir(), 'yt_%(id)s.%(ext)s'),
        'format': 'bestaudio/best',
        'ffmpeg_location': FFMPEG_EXE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192',
        }]
    }

    results = []
    # Proje kökü: scraping/.. → data/raw/ingested_videos.json
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    registry_path = os.path.join(project_root, 'data', 'raw', 'ingested_videos.json')
    seen_ids = load_ingested_registry(registry_path)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(args.url, download=False)

        entries = []
        if info.get('_type') == 'playlist':
            entries = info.get('entries', [])
        else:
            entries = [info]

        for entry in entries:
            if not entry:
                continue
            vid_url = entry.get('webpage_url') or entry.get('url')
            title = entry.get('title') or 'YouTube Video'
            vid_id = entry.get('id')
            if vid_id in seen_ids:
                print(f"⏭️  Atlandı (daha önce işlendi): {title}")
                continue

            # Videoyu indir
            downloaded_info = ydl.extract_info(vid_url, download=True)
            # M4A yolu postprocessor tarafından üretildi
            tmp_dir = tempfile.gettempdir()
            candidate = os.path.join(tmp_dir, f"yt_{downloaded_info['id']}.m4a")
            if not os.path.exists(candidate):
                # Alternatif uzantı kontrolü
                for ext in ('.m4a', '.mp3', '.webm'):
                    alt = os.path.join(tmp_dir, f"yt_{downloaded_info['id']}{ext}")
                    if os.path.exists(alt):
                        candidate = alt
                        break

            if not os.path.exists(candidate):
                print(f"Geçici ses dosyası bulunamadı: {title}")
                continue

            try:
                # Önce dry-run ile önizleme al
                resp = ingest_file(args.api, candidate, title, vid_url, downloaded_info['id'], language=args.language, dry_run=args.review)
                if not resp:
                    print(f"❌ İşlenemedi (boş yanıt): {title}")
                    continue

                if args.review:
                    preview = resp.get('informative_preview') or resp.get('preview', '')
                    est = resp.get('total_chunks_estimate')
                    first_chunks = resp.get('first_chunks') or []
                    print(f"\n--- ÖNİZLEME: {title} ---\n{preview}")
                    if args.show_full:
                        cleaned_file_rel = resp.get('cleaned_file')
                        cleaned_file_abs = os.path.join(project_root, cleaned_file_rel) if cleaned_file_rel else None
                        if cleaned_file_abs and os.path.exists(cleaned_file_abs):
                            try:
                                with open(cleaned_file_abs, 'r', encoding='utf-8') as cf:
                                    full_text = cf.read()
                                print("\n--- TAM METİN (TEMİZ) ---\n")
                                print(full_text)
                            except Exception as e:
                                print(f"Tam metin okunamadı: {e}")
                    print("\n--- İlk 3 chunk örneği ---")
                    for i, ch in enumerate(first_chunks, 1):
                        print(f"\n[Chunk {i}]\n{ch[:600]}")
                    if est is not None:
                        print(f"\n(Tahmini chunk sayısı: {est})")
                    print("\n--- SON ---\n")
                    yn = input("Bu içeriği FAISS'e ekleyelim mi? [y/N]: ").strip().lower()
                    if yn != 'y':
                        print("⏭️  Atlandı (kullanıcı onaylamadı)")
                        continue
                    # Onaylandıysa temiz metni göndererek FAISS'e ekleyelim
                    cleaned_file_rel = resp.get('cleaned_file')
                    cleaned_file_abs = os.path.join(project_root, cleaned_file_rel)
                    try:
                        print(f"Düzenlemek istersen dosya yolu: {cleaned_file_abs}")
                        input("Gerekli düzeltmeleri yapıp kaydedin. Devam etmek için Enter'a basın...")
                        with open(cleaned_file_abs, 'r', encoding='utf-8') as cf:
                            cleaned_text = cf.read()
                    except Exception as e:
                        print(f"Temiz dosya okunamadı: {e}")
                        continue

                    endpoint = f"{args.api.rstrip('/')}/ingest/transcript"
                    data = {
                        'text': cleaned_text,
                        'title': title,
                        'url': vid_url,
                        'author': 'YouTube',
                        'clean': 'false'  # zaten temiz
                    }
                    try:
                        fin = requests.post(endpoint, data=data, timeout=600)
                        fin.raise_for_status()
                        final_resp = fin.json()
                        print(f"✅ Eklendi: {title} → chunks={final_resp.get('chunks_added', final_resp.get('chars', '?'))}")
                        results.append(final_resp)
                        seen_ids.add(downloaded_info['id'])
                        save_ingested_registry(registry_path, seen_ids)
                    except Exception as e:
                        print(f"❌ Eklenemedi: {e}")
                        continue
                else:
                    # İnceleme yoksa doğrudan eklendi kabul edilir
                    print(f"✅ Eklendi: {title} → chunks={resp.get('chunks_added')}")
                    results.append(resp)
                    seen_ids.add(downloaded_info['id'])
                    save_ingested_registry(registry_path, seen_ids)
            finally:
                try:
                    os.remove(candidate)
                except Exception:
                    pass

    print(f"\nToplam eklenen: {len(results)} video")


if __name__ == '__main__':
    main()


