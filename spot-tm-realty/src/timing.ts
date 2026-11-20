// All cuts land on the music's bar grid: 96 BPM, first downbeat at 0.58 s,
// one bar = 4 beats = 2.508 s.
const FPS = 30;
const f = (s: number) => Math.round(s * FPS);

export const T = {
  drop: f(0.58), // HUD + mission panel
  bar2: f(3.09), // title slam + minimap
  bar3: f(5.6), // tape + objective
  cut: f(8.1), // cut to the house
  bar5: f(10.61), // mission complete
  end: f(13.12), // end card
  hit: f(15.0), // contact button on the music's final brass hit
};

export const TOTAL = f(17.6);
