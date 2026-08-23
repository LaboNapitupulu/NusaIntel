export function DataScene() {
  return (
    <div className="data-scene" data-reveal aria-hidden="true">
      <div className="scene-halo" />
      <div className="scene-orbit scene-orbit-one" />
      <div className="scene-orbit scene-orbit-two" />
      <div className="data-cube">
        <span className="cube-face cube-front"><i /></span>
        <span className="cube-face cube-back"><i /></span>
        <span className="cube-face cube-right"><i /></span>
        <span className="cube-face cube-left"><i /></span>
        <span className="cube-face cube-top"><i /></span>
        <span className="cube-face cube-bottom"><i /></span>
      </div>
      <div className="scene-platform scene-platform-one" />
      <div className="scene-platform scene-platform-two" />
      <span className="scene-label scene-label-trust">TRUST</span>
      <span className="scene-label scene-label-evidence">EVIDENCE</span>
      <span className="scene-label scene-label-action">ACTION</span>
    </div>
  );
}
