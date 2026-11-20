import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  Easing,
  OffthreadVideo,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import '@fontsource/anton/index.css';
import '@fontsource/bebas-neue/index.css';
import '@fontsource/cinzel/900.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/800.css';
import '@fontsource/inter/900.css';
import '@fontsource/montserrat/600.css';
import '@fontsource/montserrat/700.css';
import {T, TOTAL} from './timing';

const GOLD_GRAD =
  'linear-gradient(180deg,#FFF1B8 0%,#F6CF63 38%,#C8932E 72%,#8A5E17 100%)';
const WHITE_GRAD = 'linear-gradient(180deg,#FFFFFF 0%,#F4F4F4 55%,#C9C9C9 100%)';
const GREEN_GRAD = 'linear-gradient(180deg,#A6F58E 0%,#5CCB52 50%,#2B8A2F 100%)';
const BRAND_GOLD = '#BEAF87';

const ip = (
  f: number,
  input: number[],
  output: number[],
  easing?: (t: number) => number,
) =>
  interpolate(f, input, output, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing,
  });

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const specs = [
      '400 100px Anton',
      '400 100px "Bebas Neue"',
      '900 100px Cinzel',
      '500 40px Inter',
      '600 40px Inter',
      '700 40px Inter',
      '800 40px Inter',
      '900 40px Inter',
      '600 40px Montserrat',
      '700 40px Montserrat',
    ];
    Promise.all(specs.map((s) => document.fonts.load(s, 'ÁÉÍÓÚÑ¡!$021 abc')))
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);
};

// Text with a thick outline: an outlined copy behind a filled copy, plus an
// optional light sweep clipped to the letters.
const StrokeText: React.FC<{
  text: string;
  font: React.CSSProperties;
  stroke: number;
  strokeColor?: string;
  fill: string;
  shine?: number; // -1..2, position of the light band; outside 0..1 = hidden
}> = ({text, font, stroke, strokeColor = '#0A0A0A', fill, shine = -1}) => {
  // Padding keeps accents and descenders inside the clipped background box;
  // the negative margin on the wrapper cancels it out for layout.
  const base: React.CSSProperties = {
    ...font,
    whiteSpace: 'nowrap',
    display: 'block',
    padding: '0.28em 0.06em 0.12em',
  };
  return (
    <span style={{position: 'relative', display: 'inline-block', margin: '-0.28em -0.06em -0.12em'}}>
      <span
        style={{
          ...base,
          color: strokeColor,
          WebkitTextStroke: `${stroke}px ${strokeColor}`,
          filter: 'drop-shadow(0 10px 0 rgba(0,0,0,0.35))',
        }}
      >
        {text}
      </span>
      <span
        style={{
          ...base,
          position: 'absolute',
          left: 0,
          top: 0,
          background: fill,
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
        }}
      >
        {text}
      </span>
      {shine > -0.5 && shine < 1.5 ? (
        <span
          style={{
            ...base,
            position: 'absolute',
            left: 0,
            top: 0,
            backgroundImage:
              'linear-gradient(110deg, transparent 0%, transparent 40%, rgba(255,255,255,0.95) 50%, transparent 60%, transparent 100%)',
            backgroundSize: '300% 100%',
            backgroundPosition: `${100 - shine * 100}% 0`,
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
          }}
        >
          {text}
        </span>
      ) : null}
    </span>
  );
};

const CHAMFER =
  'polygon(22px 0, calc(100% - 22px) 0, 100% 22px, 100% calc(100% - 22px), calc(100% - 22px) 100%, 22px 100%, 0 calc(100% - 22px), 0 22px)';

// Dark game panel with gold frame, like an in-game mission prompt.
const Panel: React.FC<{
  from: number;
  to: number;
  top: number;
  heading: string;
  body: string;
  width?: number;
}> = ({from, to, top, heading, body, width = 880}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < from || frame > to + 8) return null;
  const s = spring({frame: frame - from, fps, config: {damping: 15, stiffness: 190}});
  const out = ip(frame, [to, to + 8], [1, 0]);
  const sx = interpolate(s, [0, 1], [0.08, 1]);
  const textIn = ip(frame, [from + 4, from + 11], [0, 1]);
  const shine = ip(frame, [from + 5, from + 26], [-40, 140]);
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: (1080 - width) / 2,
        width,
        opacity: Math.min(1, s * 1.6) * out,
        transform: `scaleX(${sx}) scale(${interpolate(out, [0, 1], [0.94, 1])})`,
        filter:
          'drop-shadow(0 14px 22px rgba(0,0,0,0.6)) drop-shadow(0 0 16px rgba(246,207,99,0.35))',
      }}
    >
      <div style={{clipPath: CHAMFER, background: GOLD_GRAD, padding: 4}}>
        <div
          style={{
            clipPath: CHAMFER,
            background:
              'linear-gradient(180deg, rgba(34,27,14,0.95) 0%, rgba(10,9,8,0.93) 55%, rgba(4,4,4,0.93) 100%)',
            padding: '28px 44px 34px',
            textAlign: 'center',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: '12%',
              right: '12%',
              top: 0,
              height: 3,
              background:
                'linear-gradient(90deg, transparent, rgba(255,230,160,0.95), transparent)',
            }}
          />
          <div
            style={{
              opacity: textIn,
              transform: `translateY(${(1 - textIn) * 14}px)`,
              fontFamily: 'Inter',
              fontWeight: 800,
              fontSize: 50,
              letterSpacing: 1,
              background: GOLD_GRAD,
              WebkitBackgroundClip: 'text',
              color: 'transparent',
              lineHeight: 1.15,
            }}
          >
            {heading}
          </div>
          <div
            style={{
              opacity: ip(frame, [from + 7, from + 14], [0, 1]),
              transform: `translateY(${(1 - ip(frame, [from + 7, from + 14], [0, 1])) * 14}px)`,
              fontFamily: 'Inter',
              fontWeight: 700,
              fontSize: 45,
              color: '#FFFFFF',
              marginTop: 10,
              lineHeight: 1.25,
              textShadow: '0 2px 6px rgba(0,0,0,0.8)',
            }}
          >
            {body}
          </div>
          <div
            style={{
              position: 'absolute',
              top: -40,
              bottom: -40,
              left: `${shine}%`,
              width: '16%',
              transform: 'skewX(-22deg)',
              background:
                'linear-gradient(90deg, transparent, rgba(255,226,150,0.22), transparent)',
            }}
          />
        </div>
      </div>
    </div>
  );
};

const STAR_PATH =
  'M12 1.6l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.4l-6.2 3.3L7 13.8 2 8.9l6.9-1z';

const Hud: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < T.drop || frame >= T.end) return null;

  const rollStart = T.bar5 + 8;
  const roll = ip(frame, [rollStart, rollStart + 34], [0, 1], Easing.out(Easing.cubic));
  const value = Math.round(roll * 21000000);
  const digits = String(value).padStart(8, '0');
  const moneyIn = spring({frame: frame - (T.drop + 6), fps, config: {damping: 14}});
  const moneyPulse = frame >= rollStart ? 1 + 0.08 * Math.sin(ip(frame, [rollStart, rollStart + 34], [0, Math.PI])) : 1;

  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: 84,
          right: 34,
          display: 'flex',
          gap: 6,
          filter: 'drop-shadow(0 3px 4px rgba(0,0,0,0.6))',
        }}
      >
        {[0, 1, 2, 3, 4].map((i) => {
          const pop = spring({frame: frame - (T.drop + i * 3), fps, config: {damping: 10, stiffness: 220}});
          const fillAt = T.bar5 + 6 + i * 4;
          const lit = i < 2 || frame >= fillAt;
          const burst = frame >= fillAt && i >= 2 ? spring({frame: frame - fillAt, fps, config: {damping: 8, stiffness: 260}}) : 1;
          const s = pop * (i >= 2 && frame >= fillAt ? interpolate(burst, [0, 1], [1.6, 1]) : 1);
          return (
            <svg key={i} width={64} height={64} viewBox="0 0 24 24" style={{transform: `scale(${s})`}}>
              <path
                d={STAR_PATH}
                fill={lit ? 'url(#starGold)' : 'rgba(0,0,0,0.35)'}
                stroke={lit ? '#2A1A04' : 'rgba(255,255,255,0.9)'}
                strokeWidth={1.4}
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient id="starGold" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#FFF3B0" />
                  <stop offset="0.5" stopColor="#F6C94E" />
                  <stop offset="1" stopColor="#B07A1E" />
                </linearGradient>
              </defs>
            </svg>
          );
        })}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 152,
          right: 34,
          transform: `scale(${moneyIn * moneyPulse})`,
          transformOrigin: 'right center',
        }}
      >
        <StrokeText
          text={`$${digits}`}
          font={{fontFamily: 'Bebas Neue', fontSize: 104, letterSpacing: 2, lineHeight: 1}}
          stroke={10}
          strokeColor="#06210A"
          fill={GREEN_GRAD}
        />
      </div>
    </>
  );
};

const Sparkles: React.FC<{start: number; cx: number; cy: number; count?: number; seed: string; spread?: number}> = ({
  start,
  cx,
  cy,
  count = 30,
  seed,
  spread = 420,
}) => {
  const frame = useCurrentFrame();
  const local = frame - start;
  if (local < 0 || local > 40) return null;
  return (
    <>
      {new Array(count).fill(0).map((_, i) => {
        const a = random(`${seed}a${i}`) * Math.PI * 2;
        const sp = 0.35 + random(`${seed}s${i}`) * 0.65;
        const d = ip(local, [0, 34], [0, spread * sp], Easing.out(Easing.cubic));
        const size = 10 + random(`${seed}z${i}`) * 26;
        const o = ip(local, [0, 4, 22, 38], [0, 1, 0.8, 0]);
        return (
          <svg
            key={i}
            width={size}
            height={size}
            viewBox="-10 -10 20 20"
            style={{
              position: 'absolute',
              left: cx + Math.cos(a) * d - size / 2,
              top: cy + Math.sin(a) * d * 0.7 - size / 2,
              opacity: o,
              transform: `rotate(${local * 6 + i * 20}deg)`,
              filter: 'drop-shadow(0 0 6px rgba(255,214,110,0.9))',
            }}
          >
            <path d="M0 -10 L2 -2 L10 0 L2 2 L0 10 L-2 2 L-10 0 L-2 -2 Z" fill={i % 3 === 0 ? '#FFFFFF' : '#FFD86B'} />
          </svg>
        );
      })}
    </>
  );
};

const Flash: React.FC<{at: number; peak?: number; len?: number}> = ({at, peak = 0.6, len = 7}) => {
  const frame = useCurrentFrame();
  const o = ip(frame, [at - 1, at, at + len], [0, peak, 0]);
  if (o <= 0) return null;
  return <AbsoluteFill style={{background: '#FFF6DE', opacity: o}} />;
};

const GameTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - T.bar2;
  if (local < 0 || frame >= T.cut) return null;
  const slam = spring({frame: local, fps, config: {damping: 11, stiffness: 230, mass: 0.8}});
  const scale = interpolate(slam, [0, 1], [2.3, 1]) * ip(frame, [T.bar2, T.cut], [1, 1.045]);
  const op = ip(local, [0, 3], [0, 1]) * ip(frame, [T.cut - 6, T.cut], [1, 0]);
  const shakeAmt = ip(local, [3, 12], [16, 0]);
  const sx = (random(`tx${frame}`) - 0.5) * shakeAmt;
  const sy = (random(`ty${frame}`) - 0.5) * shakeAmt;
  const shine = local < 40 ? ip(local, [6, 26], [-0.2, 1.2]) : ip(local, [92, 112], [-0.2, 1.2]);
  const glint = ip(local, [8, 16, 30], [0, 1, 0]);
  return (
    <div
      style={{
        position: 'absolute',
        top: 232,
        left: 0,
        width: 1080,
        display: 'flex',
        justifyContent: 'center',
        opacity: op,
        transform: `translate(${sx}px, ${sy}px) scale(${scale})`,
        transformOrigin: '540px 260px',
      }}
    >
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <StrokeText
          text="GRAN"
          font={{fontFamily: 'Anton', fontSize: 160, lineHeight: 0.98, letterSpacing: 4}}
          stroke={16}
          fill={WHITE_GRAD}
          shine={shine}
        />
        <div style={{marginTop: -16}}>
          <StrokeText
            text="MISIÓN"
            font={{fontFamily: 'Anton', fontSize: 198, lineHeight: 0.98, letterSpacing: 4}}
            stroke={16}
            fill={WHITE_GRAD}
            shine={shine}
          />
        </div>
        <div style={{display: 'flex', alignItems: 'flex-end', marginTop: -30}}>
          <StrokeText
            text="REAL ESTATE"
            font={{fontFamily: 'Anton', fontSize: 112, lineHeight: 1.0, letterSpacing: 3}}
            stroke={13}
            fill={WHITE_GRAD}
            shine={shine}
          />
          <div style={{position: 'relative', marginLeft: 12, marginBottom: -26}}>
            <StrokeText
              text="21"
              font={{fontFamily: 'Cinzel', fontWeight: 900, fontSize: 228, lineHeight: 1.0}}
              stroke={12}
              strokeColor="#1C1205"
              fill={GOLD_GRAD}
              shine={shine}
            />
            <svg
              width={150}
              height={150}
              viewBox="-10 -10 20 20"
              style={{
                position: 'absolute',
                left: 150,
                top: 10,
                opacity: glint,
                transform: `rotate(${local * 3}deg) scale(${0.6 + glint * 0.6})`,
                filter: 'drop-shadow(0 0 10px rgba(255,230,150,1))',
              }}
            >
              <path d="M0 -10 L1.2 -1.2 L10 0 L1.2 1.2 L0 10 L-1.2 1.2 L-10 0 L-1.2 -1.2 Z" fill="#FFFFFF" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

const Minimap: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - T.bar2;
  if (local < 0 || frame >= T.end) return null;
  const s = spring({frame: local, fps, config: {damping: 13, stiffness: 170}});
  const out = ip(frame, [T.end - 5, T.end], [1, 0]);
  const R = 140;
  const p = ip(frame, [T.bar2 + 10, T.bar5], [0, 1], Easing.inOut(Easing.cubic));
  // Route in map units: up the avenue, then right to the house.
  const HX = 70;
  const HY = -120;
  const split = 0.62;
  const player =
    p < split ? {x: 0, y: (HY * p) / split} : {x: (HX * (p - split)) / (1 - split), y: HY};
  const route =
    p < split
      ? `M ${player.x} ${player.y} L 0 ${HY} L ${HX} ${HY}`
      : `M ${player.x} ${player.y} L ${HX} ${HY}`;
  const pulse = frame >= T.bar5 ? (Math.sin((frame - T.bar5) / 3) + 1) / 2 : 0;
  const roads = [
    'M 0 -500 L 0 500',
    'M -500 -120 L 500 -120',
    'M -500 95 L 500 95',
    'M -150 -500 L -150 500',
    'M 190 -500 L 190 500',
    'M -500 -300 L 500 -300',
  ];
  const dash = -frame * 2.2;
  return (
    <div
      style={{
        position: 'absolute',
        left: 210 - R - 16,
        top: 1590 - R - 16,
        opacity: out,
        transform: `scale(${s})`,
        filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.6))',
      }}
    >
      <svg width={2 * R + 32} height={2 * R + 32} viewBox={`${-R - 16} ${-R - 16} ${2 * R + 32} ${2 * R + 32}`}>
        <defs>
          <clipPath id="mmclip">
            <circle r={R} />
          </clipPath>
        </defs>
        <circle r={R + 10} fill="rgba(5,8,10,0.75)" stroke="rgba(255,255,255,0.18)" strokeWidth={2} />
        <g clipPath="url(#mmclip)">
          <circle r={R} fill="#24343C" />
          <g transform={`translate(${-player.x * 1.0}, ${-player.y * 1.0})`}>
            {[...Array(36)].map((_, i) => {
              const bx = ((i % 6) - 3) * 110 + 18;
              const by = (Math.floor(i / 6) - 3) * 110 + 18;
              return <rect key={i} x={bx} y={by} width={74} height={74} rx={8} fill="#2F444E" />;
            })}
            {roads.map((d, i) => (
              <path key={i} d={d} stroke="#8E9CA2" strokeWidth={20} strokeLinecap="round" fill="none" />
            ))}
            <path d={route} stroke="#F6C94E" strokeWidth={9} fill="none" strokeLinejoin="round" />
            <path
              d={route}
              stroke="#FFF3C4"
              strokeWidth={4}
              fill="none"
              strokeDasharray="10 14"
              strokeDashoffset={dash}
            />
            <g transform={`translate(${HX}, ${HY})`}>
              <circle r={30 + pulse * 14} fill="rgba(246,201,78,0.25)" />
              <circle r={27} fill="#F6C94E" stroke="#1C1205" strokeWidth={3} />
              <path d="M -14 2 L 0 -12 L 14 2 L 10 2 L 10 13 L -10 13 L -10 2 Z" fill="#FFFFFF" stroke="#1C1205" strokeWidth={2} strokeLinejoin="round" />
              <rect x={-3} y={5} width={6} height={8} fill="#1C1205" />
            </g>
          </g>
          <path d="M 0 -16 L 12 12 L 0 6 L -12 12 Z" fill="#FFFFFF" stroke="#0A0A0A" strokeWidth={3} strokeLinejoin="round" />
        </g>
        <path
          d={`M ${Math.cos((20 * Math.PI) / 180) * (R + 5)} ${Math.sin((20 * Math.PI) / 180) * (R + 5)} A ${R + 5} ${R + 5} 0 0 1 ${Math.cos((150 * Math.PI) / 180) * (R + 5)} ${Math.sin((150 * Math.PI) / 180) * (R + 5)}`}
          stroke="#38D1F0"
          strokeWidth={8}
          fill="none"
          strokeLinecap="round"
        />
        <circle cx={0} cy={-R - 2} r={17} fill="#0A0A0A" stroke="rgba(255,255,255,0.7)" strokeWidth={2} />
        <text x={0} y={-R + 5} textAnchor="middle" fontFamily="Inter" fontWeight={800} fontSize={20} fill="#FFFFFF">
          N
        </text>
      </svg>
    </div>
  );
};

const Tape: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - T.bar3;
  if (local < 0 || frame >= T.cut) return null;
  const s = spring({frame: local, fps, config: {damping: 17, stiffness: 150}});
  const x = interpolate(s, [0, 1], [-1800, 0]);
  const out = ip(frame, [T.cut - 6, T.cut], [1, 0]);
  return (
    <div
      style={{
        position: 'absolute',
        left: -260,
        top: 985,
        width: 1600,
        height: 116,
        opacity: out,
        transform: `translateX(${x}px) rotate(-9deg)`,
        background: 'linear-gradient(180deg,#FFE65A 0%,#F7C600 55%,#D7A500 100%)',
        boxShadow: '0 12px 26px rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderTop: '4px solid rgba(0,0,0,0.25)',
        borderBottom: '4px solid rgba(0,0,0,0.3)',
      }}
    >
      <div
        style={{
          fontFamily: 'Anton',
          fontSize: 70,
          color: '#111111',
          letterSpacing: 2,
          transform: 'skewX(-10deg)',
          whiteSpace: 'nowrap',
        }}
      >
        ¡TU CASA TE ESTÁ ESPERANDO!
      </div>
    </div>
  );
};

const MissionComplete: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - T.bar5;
  if (local < 0 || frame >= T.end) return null;
  const slam = spring({frame: local, fps, config: {damping: 10, stiffness: 240, mass: 0.8}});
  const scale = interpolate(slam, [0, 1], [2.4, 1]);
  const op = ip(local, [0, 3], [0, 1]) * ip(frame, [T.end - 6, T.end], [1, 0]);
  const shakeAmt = ip(local, [3, 12], [14, 0]);
  const sx = (random(`mx${frame}`) - 0.5) * shakeAmt;
  const sy = (random(`my${frame}`) - 0.5) * shakeAmt;
  const shine = ip(local, [6, 26], [-0.2, 1.2]);
  const sub = ip(local, [9, 16], [0, 1]);
  const bonus = spring({frame: local - 15, fps, config: {damping: 9, stiffness: 220}});
  return (
    <>
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse 80% 40% at 50% 30%, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 100%)',
          opacity: op,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 300,
          left: 0,
          width: 1080,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: op,
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transform: `translate(${sx}px, ${sy}px) scale(${scale})`,
          }}
        >
          <StrokeText
            text="¡MISIÓN"
            font={{fontFamily: 'Anton', fontSize: 190, lineHeight: 1.0, letterSpacing: 4}}
            stroke={16}
            strokeColor="#1C1205"
            fill={GOLD_GRAD}
            shine={shine}
          />
          <div style={{marginTop: -10}}>
            <StrokeText
              text="CUMPLIDA!"
              font={{fontFamily: 'Anton', fontSize: 190, lineHeight: 1.0, letterSpacing: 4}}
              stroke={16}
              strokeColor="#1C1205"
              fill={GOLD_GRAD}
              shine={shine}
            />
          </div>
        </div>
        <div
          style={{
            marginTop: 26,
            opacity: sub,
            transform: `translateY(${(1 - sub) * 20}px)`,
            fontFamily: 'Inter',
            fontWeight: 900,
            fontSize: 54,
            letterSpacing: 8,
            color: '#FFFFFF',
            textShadow: '0 3px 0 #000, 0 0 18px rgba(0,0,0,0.8)',
          }}
        >
          BIENVENIDO A CASA
        </div>
        <div style={{marginTop: 16, transform: `scale(${Math.max(0, bonus)})`}}>
          <StrokeText
            text="PATRIMONIO +100"
            font={{fontFamily: 'Bebas Neue', fontSize: 100, letterSpacing: 3, lineHeight: 1}}
            stroke={10}
            strokeColor="#06210A"
            fill={GREEN_GRAD}
          />
        </div>
      </div>
      <Sparkles start={T.bar5} cx={540} cy={470} seed="mc" count={34} spread={520} />
    </>
  );
};

const Disclaimer: React.FC = () => {
  const frame = useCurrentFrame();
  if (frame >= T.end) return null;
  return (
    <div
      style={{
        position: 'absolute',
        right: 36,
        top: 1688,
        textAlign: 'right',
        fontFamily: 'Inter',
        fontWeight: 600,
        fontSize: 26,
        lineHeight: 1.3,
        color: '#FFFFFF',
        textShadow: '0 2px 4px rgba(0,0,0,0.9)',
        opacity: ip(frame, [T.drop, T.drop + 10], [0, 1]),
      }}
    >
      Cada Oficina es de Propiedad
      <br />y Operación Independiente.
    </div>
  );
};

const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - T.end;
  if (local < 0) return null;
  const bg = ip(local, [0, 6], [0, 1]);
  const logo = ip(local, [6, 20], [0, 1], Easing.out(Easing.cubic));
  const spacing = interpolate(logo, [0, 1], [0.22, 0.02]);
  const line = ip(local, [16, 32], [0, 1], Easing.out(Easing.cubic));
  const city = ip(local, [22, 34], [0, 1]);
  const shine = ip(local, [20, 44], [-0.2, 1.2]);
  const btn = spring({frame: frame - T.hit, fps, config: {damping: 9, stiffness: 200}});
  const glow = frame >= T.hit ? 0.55 + 0.45 * Math.sin((frame - T.hit) / 5) : 0;
  const disc = ip(local, [26, 38], [0, 1]);
  return (
    <AbsoluteFill style={{opacity: bg}}>
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse 70% 38% at 50% 46%, rgba(190,175,135,0.16) 0%, rgba(5,5,5,1) 70%), #050505',
        }}
      />
      {new Array(46).fill(0).map((_, i) => {
        const x = random(`dx${i}`) * 1080;
        const y0 = random(`dy${i}`) * 1920;
        const y = (y0 - local * (0.6 + random(`dv${i}`) * 1.4) + 1920) % 1920;
        const size = 2 + random(`ds${i}`) * 5;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: '50%',
              background: BRAND_GOLD,
              opacity: 0.15 + random(`do${i}`) * 0.45,
              boxShadow: `0 0 ${size * 2}px ${BRAND_GOLD}`,
            }}
          />
        );
      })}
      <div
        style={{
          position: 'absolute',
          top: 700,
          width: 1080,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: logo,
          transform: `translateY(${(1 - logo) * 30}px)`,
        }}
      >
        <div style={{display: 'flex', alignItems: 'flex-start'}}>
          <StrokeText
            text="CENTURY 21"
            font={{
              fontFamily: 'Montserrat',
              fontWeight: 700,
              fontSize: 120,
              letterSpacing: `${spacing}em`,
              lineHeight: 1,
            }}
            stroke={0}
            strokeColor="transparent"
            fill="linear-gradient(180deg,#FFFFFF,#E9E9E9)"
            shine={shine}
          />
          <span style={{fontFamily: 'Inter', fontWeight: 600, fontSize: 24, color: '#FFFFFF', marginLeft: 4, marginTop: 84}}>®</span>
        </div>
        <div
          style={{
            fontFamily: 'Montserrat',
            fontWeight: 600,
            fontSize: 76,
            color: '#FFFFFF',
            marginTop: 14,
            letterSpacing: `${spacing * 0.6}em`,
          }}
        >
          TM Realty
        </div>
        <div style={{width: 560 * line, height: 3, background: BRAND_GOLD, marginTop: 44, boxShadow: `0 0 12px ${BRAND_GOLD}`}} />
        <div
          style={{
            marginTop: 34,
            opacity: city,
            fontFamily: 'Inter',
            fontWeight: 700,
            fontSize: 42,
            letterSpacing: '0.24em',
            color: BRAND_GOLD,
          }}
        >
          METEPEC | TOLUCA
        </div>
        <div
          style={{
            marginTop: 90,
            transform: `scale(${frame >= T.hit ? btn : 0})`,
            padding: '26px 60px',
            border: `3px solid ${BRAND_GOLD}`,
            borderRadius: 14,
            background: 'rgba(190,175,135,0.14)',
            boxShadow: `0 0 ${18 + glow * 26}px rgba(190,175,135,${0.35 + glow * 0.35})`,
            fontFamily: 'Inter',
            fontWeight: 800,
            fontSize: 50,
            letterSpacing: '0.06em',
            color: '#FFFFFF',
          }}
        >
          CONTÁCTANOS HOY
        </div>
      </div>
      <div
        style={{
          position: 'absolute',
          top: 1712,
          width: 1080,
          textAlign: 'center',
          fontFamily: 'Inter',
          fontWeight: 500,
          fontSize: 30,
          color: '#D8D8D8',
          opacity: disc,
        }}
      >
        Cada Oficina es de Propiedad y Operación Independiente.
      </div>
      <AbsoluteFill style={{background: '#000', opacity: ip(frame, [TOTAL - 8, TOTAL - 1], [0, 1])}} />
    </AbsoluteFill>
  );
};

const ClipA: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <OffthreadVideo src={staticFile('clipA.mp4')} muted playbackRate={8 / 8.15} />
      <AbsoluteFill style={{background: '#000', opacity: ip(frame, [0, 9], [1, 0])}} />
    </AbsoluteFill>
  );
};

const ClipB: React.FC = () => {
  const frame = useCurrentFrame();
  const s = ip(frame, [0, 10], [1.1, 1], Easing.out(Easing.cubic));
  return (
    <AbsoluteFill style={{transform: `scale(${s})`}}>
      <OffthreadVideo src={staticFile('clipB.mp4')} muted />
    </AbsoluteFill>
  );
};

export const Spot: React.FC = () => {
  useFonts();
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <Sequence from={0} durationInFrames={T.cut}>
        <ClipA />
      </Sequence>
      <Sequence from={T.cut} durationInFrames={T.end - T.cut}>
        <ClipB />
      </Sequence>
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.38) 0%, rgba(0,0,0,0) 17%, rgba(0,0,0,0) 72%, rgba(0,0,0,0.42) 100%), radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.38) 100%)',
        }}
      />
      <Panel from={T.drop} to={T.bar2 - 4} top={430} heading="MISIÓN INICIO:" body="Comprar una casa nueva." width={820} />
      <GameTitle />
      <Sparkles start={T.bar2} cx={540} cy={560} seed="ti" count={30} spread={480} />
      <Tape />
      <Panel
        from={T.bar3 + 6}
        to={T.cut - 6}
        top={1175}
        heading="Objetivo:"
        body="Encuentra la casa de tus sueños en Metepec o Toluca y hazla tuya."
        width={900}
      />
      <Panel
        from={T.cut + 6}
        to={T.bar5 - 4}
        top={360}
        heading="OBJETIVO ACTUALIZADO:"
        body="Compra, vende o renta con expertos de tu lado."
        width={900}
      />
      <MissionComplete />
      <Minimap />
      <Hud />
      <Disclaimer />
      <Flash at={T.bar2} peak={0.55} />
      <Flash at={T.cut} peak={0.85} len={6} />
      <Flash at={T.bar5} peak={0.5} />
      <EndCard />
    </AbsoluteFill>
  );
};
