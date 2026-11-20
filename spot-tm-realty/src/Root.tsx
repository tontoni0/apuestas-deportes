import React from 'react';
import {Composition} from 'remotion';
import {Spot} from './Spot';
import {TOTAL} from './timing';

export const Root: React.FC = () => (
  <Composition
    id="Spot"
    component={Spot}
    durationInFrames={TOTAL}
    fps={30}
    width={1080}
    height={1920}
  />
);
