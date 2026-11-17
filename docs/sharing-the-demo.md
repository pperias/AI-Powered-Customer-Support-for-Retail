# Sharing the demo

Use ngrok or Cloudflared to let a teammate open the app running on your laptop.

```bash
ngrok http 8000
# or
cloudflared tunnel --url http://localhost:8000
```

Replace `8000` with the port your chat UI uses. The address stops working when you close the command. Use mock data only.
