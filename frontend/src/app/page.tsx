"use client";

import { motion } from "framer-motion";
import { Shield, Activity, Loader2 } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 relative overflow-hidden">
      {/* Background glow effect */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[120px]" />
        <div className="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Logo & Title */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 flex flex-col items-center gap-6"
      >
        <motion.div
          animate={{
            boxShadow: [
              "0 0 20px rgba(34,211,238,0.2)",
              "0 0 40px rgba(34,211,238,0.4)",
              "0 0 20px rgba(34,211,238,0.2)",
            ],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 border border-cyan-500/30 flex items-center justify-center"
        >
          <Shield className="w-10 h-10 text-cyan-400" />
        </motion.div>

        <div className="text-center">
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
            SHERLOCK
          </h1>
          <p className="mt-2 text-slate-400 text-lg font-light tracking-wide">
            Fraud Detection & Ring Analysis Engine
          </p>
        </div>
      </motion.div>

      {/* Status indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.5 }}
        className="relative z-10 flex items-center gap-3 px-6 py-3 rounded-full border border-[#21262d] bg-[#161b22]/80 backdrop-blur-sm"
      >
        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
        <span className="text-sm text-slate-400 font-medium tracking-wide">
          Initializing...
        </span>
        <Activity className="w-4 h-4 text-emerald-400" />
      </motion.div>

      {/* Version badge */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.5 }}
        className="relative z-10 text-xs text-slate-600 font-mono"
      >
        v0.1.0 — skeleton
      </motion.p>
    </main>
  );
}
