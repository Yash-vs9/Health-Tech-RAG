export default function TeamCard({ name, role }) {
  return (
    <div className="team-card">
      <h3>{name}</h3>
      <p>{role}</p>
    </div>
  );
}