import Navbar from "../components/Navbar";
import FeatureCard from "../components/FeatureCard";
import TeamCard from "../components/TeamCard";

export default function Home() {
  return (
    <>
      <Navbar />

      <section className="hero">
        <h1>Health-Tech AI Assistant</h1>

        <p>
          AI-powered chatbot that helps users analyze medical documents,
          answer health-related questions, and provide quick insights.
        </p>

        <div className="hero-buttons">
          <button>Get Started</button>
          <button>Learn More</button>
        </div>
      </section>

      <section className="features" id="features">
        <h2>Our Features</h2>

        <div className="feature-grid">
          <FeatureCard
            title="Upload Reports"
            description="Upload PDF medical reports securely."
          />

          <FeatureCard
            title="AI Chat"
            description="Ask health-related questions instantly."
          />

          <FeatureCard
            title="Smart Search"
            description="Find information inside uploaded reports."
          />

          <FeatureCard
            title="Secure Data"
            description="Your medical data stays protected."
          />
        </div>
      </section>

      <section className="team" id="team">
        <h2>Our Team</h2>

        <div className="team-grid">
          <TeamCard
            name="Anushka barman"
            role="Frontend Developer"
          />
        </div>
      </section>
    </>
  );
}