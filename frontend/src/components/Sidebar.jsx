import {
  LayoutDashboard,
  FileSearch,
  Bot,
  GitBranch,
  Gavel,
  Activity,
} from "lucide-react";

function Sidebar({ activePage, setActivePage }) {
  const menuItems = [
    {
      name: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Evidence",
      icon: FileSearch,
    },
    {
      name: "Agents",
      icon: Bot,
    },
    {
      name: "Evidence Graph",
      icon: GitBranch,
    },
    {
      name: "Decision",
      icon: Gavel,
    },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-logo">P</div>

        <div>
          <h2>PARALLAX</h2>
          <span>Decision Intelligence</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;

          return (
            <button
              key={item.name}
              className={`nav-item ${activePage === item.name ? "active" : ""}`}
              onClick={() => setActivePage(item.name)}
            >
              <Icon size={19} />
              <span>{item.name}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="system-status">
          <Activity size={17} />
          <div>
            <strong>System Online</strong>
            <span>Backend connected</span>
          </div>
        </div>

        <div className="version">PARALLAX v1.0</div>
      </div>
    </aside>
  );
}

export default Sidebar;
