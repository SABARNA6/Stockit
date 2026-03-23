import { Icon } from "../utils";

export default function PageHeader({ iconKey, title, sub, action }) {
  const icon = Icon[iconKey];
  return (
    <div className="portfolio-page-header">
      <div className="portfolio-page-header__main">
        <div className="portfolio-page-header__icon">{icon}</div>
        <div className="portfolio-page-header__text">
          <h1 className="portfolio-page-header__title">{title}</h1>
          {sub && <p className="portfolio-page-header__sub">{sub}</p>}
        </div>
      </div>
      {action && <div className="portfolio-page-header__action">{action}</div>}
    </div>
  );
}
