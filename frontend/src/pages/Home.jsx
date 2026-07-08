import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Navbar from "../components/Navbar";
import FeatureCard from "../components/FeatureCard";
import TeamCard from "../components/TeamCard";
import { ArrowRight, FileText, BarChart3, Lock } from "lucide-react";

const features = [
  { icon: "upload", title: "Secure Document Upload", description: "Upload bank statements, PDFs, and financial reports with bank-grade encryption." },
  { icon: "chat", title: "AI Financial Assistant", description: "Ask questions about your finances and get instant, accurate answers powered by AI." },
  { icon: "search", title: "Smart Transaction Search", description: "Find specific transactions, patterns, and anomalies across all your documents." },
  { icon: "shield", title: "Enterprise Security", description: "Your financial data is protected with AES-256 encryption and SOC 2 compliance." },
];

const stats = [
  { value: "10K+", label: "Documents Analyzed" },
  { value: "99.2%", label: "Accuracy Rate" },
  { value: "256-bit", label: "Encryption" },
];

export default function Home() {
  return (
    <>
      <div className="grid-bg" />
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <Navbar />

      <section className="hero">
        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <motion.div
            className="hero-badge"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            AI-Powered Banking
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            Intelligent Financial<br />Document Analysis
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            Upload bank statements, financial reports, and transaction records.
            Get instant AI-powered insights, summaries, and answers to your banking queries.
          </motion.p>

          <motion.div
            className="hero-buttons"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <Link to="/signup" className="btn-hero-primary">
              Start Free Trial
              <ArrowRight size={18} style={{ marginLeft: 8, verticalAlign: 'middle' }} />
            </Link>
            <a href="#features" className="btn-hero-secondary">Learn More</a>
          </motion.div>

          <motion.div
            className="hero-stats"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                className="stat"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.7 + i * 0.1 }}
              >
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
              </motion.div>
            )).reduce((acc, el, i) => {
              if (i > 0) acc.push(<div key={`div-${i}`} className="stat-divider" />);
              acc.push(el);
              return acc;
            }, [])}
          </motion.div>
        </motion.div>
      </section>

      <section className="features" id="features">
        <div className="section-container">
          <motion.div
            className="section-header"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
          >
            <span className="section-badge">Features</span>
            <h2>Smart Banking, Smarter Decisions</h2>
            <p>Everything you need to analyze and understand your financial documents</p>
          </motion.div>

          <div className="feature-grid">
            {features.map((f, i) => (
              <FeatureCard key={f.title} {...f} index={i} />
            ))}
          </div>
        </div>
      </section>

      <section className="team" id="team">
        <div className="section-container">
          <motion.div
            className="section-header"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
          >
            <span className="section-badge">Team</span>
            <h2>Built by Experts</h2>
            <p>The minds behind FinAssist AI</p>
          </motion.div>

          <div className="team-grid">
            <div className="team-row">
              <TeamCard name="Akansha" index={0} />
              <TeamCard name="Ananya" index={1} />
              <TeamCard name="Anushka" index={2} />
              <TeamCard name="Aryan" index={3} />
              <TeamCard name="Isha" index={4} />
            </div>
            <div className="team-row">
              <TeamCard name="Lakshya" index={5} />
              <TeamCard name="Soojal" index={6} />
              <TeamCard name="Tejasva" index={7} />
              <TeamCard name="Yash" index={8} />
            </div>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-container">
          <div className="footer-brand">
            <div className="logo">
              <div className="logo-icon">FA</div>
              <span>FinAssist AI</span>
            </div>
            <p>AI-powered banking document analysis platform.</p>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 FinAssist AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </>
  );
}
