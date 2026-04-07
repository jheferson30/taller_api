export default function PageHero({ titulo, subtitulo, badge, action }) {
  return (
    <div className="page-hero">
      <div>
        <h1 className="page-hero-title">{titulo}</h1>
        <p className="page-hero-sub">{subtitulo}</p>
      </div>
      <div className="page-hero-right">
        {badge != null && (
          <div className="page-hero-badge">{badge}</div>
        )}
        {action}
      </div>
    </div>
  );
}
