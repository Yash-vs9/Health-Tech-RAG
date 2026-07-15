import { motion } from "framer-motion";
import { Upload, MessageSquare, Search, Shield } from "lucide-react";

const icons = {
  upload: <Upload size={28} />,
  chat: <MessageSquare size={28} />,
  search: <Search size={28} />,
  shield: <Shield size={28} />,
};

export default function FeatureCard({ icon, title, description, index }) {
  return (
    <motion.div
      className="feature-card"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
      whileHover={{
        rotateX: 3,
        rotateY: -2,
        scale: 1.02,
        transition: { duration: 0.3 }
      }}
      style={{ transformStyle: "preserve-3d" }}
    >
      <div className="feature-icon">{icons[icon]}</div>
      <h3>{title}</h3>
      <p>{description}</p>
    </motion.div>
  );
}
