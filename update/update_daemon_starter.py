import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app",
                host="0.0.0.0",
                port=443,
                reload=False,
                log_level="info",
                ssl_keyfile='/etc/letsencrypt/live/kiberded.ga/privkey.pem',
                ssl_certfile='/etc/letsencrypt/live/kiberded.ga/fullchain.pem'
                )
