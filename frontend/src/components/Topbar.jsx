import { Search, Bell, CircleHelp, ChevronRight } from "lucide-react";

function Topbar({ activePage }) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>PARALLAX</span>
        <ChevronRight size={15} />
        <strong>{activePage}</strong>
      </div>

      <div className="topbar-actions">
        <div className="search-box">
          <Search size={17} />
          <input type="text" placeholder="Search evidence..." />
        </div>

        <button className="icon-button">
          <CircleHelp size={19} />
        </button>

        <button className="icon-button notification">
          <Bell size={19} />
          <span></span>
        </button>

        <div className="user-avatar">P</div>
      </div>
    </header>
  );
}

export default Topbar;
