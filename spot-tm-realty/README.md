# Spot Century 21 TM Realty: misión

Spot vertical de 17.6 s (1080×1920, 30 fps) con estilo de videojuego de mundo abierto.

## Archivos

- `CENTURY21_TM_REALTY_SPOT_MISION.mp4`: video final con audio.
- `src/`: animación de la interfaz en Remotion (panel de misión, título, estrellas, dinero, minimapa, cinta, misión cumplida y cierre).
- `public/clipA.mp4`, `public/clipB.mp4`: tomas generadas con Veo 3.1 Lite.
- `gen/a2.png`, `gen/b2.png`: fotogramas base de cada toma.
- `audio/`: música instrumental y efectos generados con ElevenLabs.
- `mix_audio.sh`: mezcla de música, ambiente y efectos.

## Volver a generar

```bash
npm install
npx remotion render src/index.ts Spot out/video_silent.mp4 --codec=h264 --crf=16 --muted
./mix_audio.sh
ffmpeg -i out/video_silent.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest CENTURY21_TM_REALTY_SPOT_MISION.mp4
```

Los tiempos de cada animación están en `src/timing.ts`.
