export default function TeamCard({ name, role }) {
  const initials = name.split(" ").map((n) => n[0]).join("");

  return (
    <div className="team-card">
      <div className="team-avatar">{initials}</div>
      <h3>{name}</h3>
      <p>{role}</p>
    </div>
  );
}
