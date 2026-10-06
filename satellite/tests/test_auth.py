from app.services.downloader import CopernicusDownloader


downloader = CopernicusDownloader()

token = downloader.get_access_token()

print("Copernicus authentication successful.")
print("Token received:", bool(token))
print("Token length:", len(token))