import { motion } from "framer-motion";

export default function TeamCard({ name, role, index }) {
  const initials = name.split(" ").map((n) => n[0]).join("");

  return (
    <motion.div
      className="team-card"
      initial={{ opacity: 0, y: 30, rotateY: -5 }}
      whileInView={{ opacity: 1, y: 0, rotateY: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6, delay: index * 0.15, ease: "easeOut" }}
      whileHover={{
        rotateY: 5,
        rotateX: -3,
        scale: 1.03,
        transition: { duration: 0.3 }
      }}
      style={{ transformStyle: "preserve-3d" }}
    >
      <motion.div
        className="team-avatar"
        whileHover={{ rotate: -8, scale: 1.1 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        {initials}
      </motion.div>
      <h3>{name}</h3>
      <p>{role}</p>
    </motion.div>
  );
}
