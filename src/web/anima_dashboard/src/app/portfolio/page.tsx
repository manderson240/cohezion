"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, ChevronRight } from "lucide-react";

// lucide-react dropped its brand icons (Github, Linkedin) in 1.x; the dev server refused
// to compile this page on the missing exports. Inline the two marks (Simple Icons paths).
function Github({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

function Linkedin({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

// Portfolio Pillar Card Component
interface PillarCardProps {
  title: string;
  description: string;
  icon: string;
  demoPath: string;
  blogPath: string;
  gradient: string;
  status: "live" | "building" | "planned";
}

function PillarCard({ title, description, icon, demoPath, blogPath, gradient, status }: PillarCardProps) {
  return (
    <div className={`group relative bg-gradient-to-br ${gradient} p-[1px] rounded-2xl overflow-hidden transition-all duration-300 hover:scale-[1.02]`}>
      {/* Animated border glow */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000" />

      <div className="relative bg-[#0a0a0a] rounded-2xl p-8 h-full flex flex-col">
        {/* Status Badge */}
        <div className="absolute top-4 right-4">
          <span className={`text-[10px] font-mono px-2 py-1 rounded ${
            status === "live" ? "bg-emerald-500/20 text-emerald-400" :
            status === "building" ? "bg-amber-500/20 text-amber-400" :
            "bg-gray-500/20 text-gray-400"
          }`}>
            {status.toUpperCase()}
          </span>
        </div>

        {/* Icon */}
        <div className="text-6xl mb-6">{icon}</div>

        {/* Title */}
        <h3 className="text-2xl font-bold mb-3 font-mono text-white">
          {title}
        </h3>

        {/* Description */}
        <p className="text-gray-400 text-sm mb-6 flex-grow leading-relaxed">
          {description}
        </p>

        {/* Action Buttons */}
        <div className="flex gap-3">
          {status === "live" && (
            <>
              <Link
                href={demoPath}
                className="flex-1 py-2 px-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg text-xs font-mono font-bold text-white transition-all flex items-center justify-center gap-2 group/btn"
              >
                <span>DEMO</span>
                <ChevronRight className="w-3 h-3 group-hover/btn:translate-x-1 transition-transform" />
              </Link>
              <Link
                href={blogPath}
                className="flex-1 py-2 px-4 bg-transparent hover:bg-white/5 border border-white/10 rounded-lg text-xs font-mono font-bold text-gray-300 transition-all"
              >
                READ MORE
              </Link>
            </>
          )}
          {status === "building" && (
            <div className="flex-1 py-2 px-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs font-mono font-bold text-amber-400 text-center">
              COMING SOON
            </div>
          )}
          {status === "planned" && (
            <div className="flex-1 py-2 px-4 bg-gray-500/10 border border-gray-500/20 rounded-lg text-xs font-mono font-bold text-gray-500 text-center">
              PLANNED
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PortfolioPage() {
  const [hoveredStat, setHoveredStat] = useState<string | null>(null);

  const pillars: PillarCardProps[] = [
    {
      title: "FLUME VAE",
      description: "Continuous latent navigation through 256-dimensional software state space. Trained on git commit histories to enable smooth interpolation between discrete code snapshots.",
      icon: "🌊",
      demoPath: "/portfolio/flume",
      blogPath: "/portfolio/blog/flume-vae",
      gradient: "from-cyan-500/20 via-blue-500/20 to-purple-500/20",
      status: "live",
    },
    {
      title: "Compound Loop",
      description: "Self-improving infrastructure that learns from every execution. Each cycle refines skills, optimizes routing, and improves coherence through automated retrospection.",
      icon: "♾️",
      demoPath: "/portfolio/compound",
      blogPath: "/portfolio/blog/compound-engineering",
      gradient: "from-emerald-500/20 via-green-500/20 to-teal-500/20",
      status: "building",
    },
    {
      title: "Universe Simulation",
      description: "12-dimensional manifold engine for agent training. SPIN-based information geometry enables continuous state spaces and coherence-based navigation.",
      icon: "🌌",
      demoPath: "/", // Points to existing Anima Dashboard
      blogPath: "/portfolio/blog/universe-simulation",
      gradient: "from-purple-500/20 via-pink-500/20 to-rose-500/20",
      status: "live",
    },
    {
      title: "Multi-Agent Swarm",
      description: "Cost-aware orchestration of specialist agents (Architect, Engineer, QHW, QAlgo, Biologist) with democratic debate and consensus mechanisms.",
      icon: "🐝",
      demoPath: "/portfolio/swarm",
      blogPath: "/portfolio/blog/swarm-orchestration",
      gradient: "from-amber-500/20 via-orange-500/20 to-red-500/20",
      status: "building",
    },
    {
      title: "Evaluation Infrastructure",
      description: "Trajectory-based assessment through coherence gates. Evaluates agent behavior in continuous spaces rather than discrete accuracy metrics.",
      icon: "📊",
      demoPath: "/portfolio/evaluation",
      blogPath: "/portfolio/blog/evaluation-trajectories",
      gradient: "from-indigo-500/20 via-violet-500/20 to-purple-500/20",
      status: "planned",
    },
  ];

  const stats = [
    { label: "Test Suite", value: "4,658", suffix: "tests", detail: "Comprehensive coverage" },
    { label: "Compound Cycles", value: "55+", suffix: "sessions", detail: "Self-improving infrastructure" },
    { label: "Production APIs", value: "2", suffix: "live", detail: "FLUME VAE + A2A Protocol" },
    { label: "Type Coverage", value: "100%", suffix: "mypy strict", detail: "Full type safety" },
  ];

  return (
    <div className="min-h-screen bg-[#000000] text-white">
      {/* Animated Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[150px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[150px] animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      <div className="relative z-10">
        {/* Header Navigation */}
        <nav className="border-b border-white/10 backdrop-blur-xl bg-black/50">
          <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <Link href="/" className="text-xl font-bold font-mono text-cyan-400">
              COHEZION
            </Link>
            <div className="flex gap-6 items-center">
              <Link href="/" className="text-sm font-mono text-gray-400 hover:text-white transition-colors">
                LIVE DEMO
              </Link>
              <Link href="#pillars" className="text-sm font-mono text-gray-400 hover:text-white transition-colors">
                PORTFOLIO
              </Link>
              <a href="https://github.com/manderson240/cohezion" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors" title="GitHub Repository">
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="max-w-6xl mx-auto px-6 py-24 text-center">
          <div className="inline-block mb-6 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-full">
            <span className="text-xs font-mono text-cyan-400 tracking-widest">
              RESEARCH ENGINEER PORTFOLIO
            </span>
          </div>

          <h1 className="text-6xl md:text-7xl font-bold mb-8 font-mono tracking-tight">
            Self-Improving
            <br />
            <span className="bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 text-transparent bg-clip-text">
              AI Infrastructure
            </span>
          </h1>

          <p className="text-xl text-gray-400 mb-12 max-w-3xl mx-auto leading-relaxed">
            Compound AI orchestration with <strong className="text-white">12D universe simulation</strong>,
            multi-agent swarm coordination, and infrastructure that <strong className="text-white">learns from every execution</strong>.
          </p>

          {/* CTA Buttons */}
          <div className="flex gap-4 justify-center mb-16">
            <Link
              href="/"
              className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-mono font-bold hover:scale-105 transition-transform flex items-center gap-2"
            >
              <span>EXPLORE LIVE DEMO</span>
              <ChevronRight className="w-5 h-5" />
            </Link>
            <Link
              href="#pillars"
              className="px-8 py-4 bg-white/10 border border-white/20 rounded-xl text-white font-mono font-bold hover:bg-white/20 transition-all"
            >
              VIEW PORTFOLIO
            </Link>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="relative bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6 hover:border-cyan-500/30 transition-all cursor-pointer group"
                onMouseEnter={() => setHoveredStat(stat.label)}
                onMouseLeave={() => setHoveredStat(null)}
              >
                <div className="text-3xl font-bold font-mono mb-1 bg-gradient-to-r from-cyan-400 to-purple-400 text-transparent bg-clip-text">
                  {stat.value}
                </div>
                <div className="text-xs text-gray-500 font-mono mb-1">{stat.suffix}</div>
                <div className="text-[10px] text-gray-600 font-mono">{stat.label}</div>

                {/* Tooltip */}
                {hoveredStat === stat.label && (
                  <div className="absolute -top-12 left-1/2 -translate-x-1/2 px-3 py-2 bg-black border border-cyan-500/30 rounded-lg text-xs text-cyan-400 font-mono whitespace-nowrap">
                    {stat.detail}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Problem/Solution Section */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-12">
            <h2 className="text-3xl font-bold mb-8 font-mono text-center">
              The Compound Engineering Thesis
            </h2>

            <div className="space-y-8">
              <div>
                <h3 className="text-lg font-bold text-red-400 mb-3 font-mono flex items-center gap-2">
                  <span className="text-2xl">❌</span> THE PROBLEM
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  Current AI systems don't compound—each task starts from scratch. Every execution wastes tokens
                  re-discovering patterns. Infrastructure remains static while models evolve.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-bold text-emerald-400 mb-3 font-mono flex items-center gap-2">
                  <span className="text-2xl">✅</span> THE SOLUTION
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  <strong className="text-white">Cohezion's compound loop</strong>: execute → reflect → refine → repeat.
                  Each cycle updates skills, optimizes routing, and improves coherence. The infrastructure learns.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-bold text-cyan-400 mb-3 font-mono flex items-center gap-2">
                  <span className="text-2xl">📈</span> THE PROOF
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  <strong className="text-white">579 modules</strong>, <strong className="text-white">4,426 tests</strong>,
                  <strong className="text-white"> 99.9% pass rate</strong>—all refined through 55+ compound cycles.
                  Cost savings: 27.3%. Cache hit rate: 95%. All automated.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Portfolio Pillars */}
        <section id="pillars" className="max-w-7xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4 font-mono">
              Five Portfolio Pillars
            </h2>
            <p className="text-gray-400 text-lg">
              Interactive demonstrations of novel AI infrastructure research
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {pillars.map((pillar) => (
              <PillarCard key={pillar.title} {...pillar} />
            ))}
          </div>
        </section>

        {/* Technical Highlights */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="text-3xl font-bold mb-12 font-mono text-center">
            Technical Highlights
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { title: "Novel Architecture", detail: "SPIN information theory → 12D manifold design" },
              { title: "Production-Ready", detail: "99.9% test pass rate, type-hinted, CI/CD" },
              { title: "Scalability", detail: "510 K-Search cycles in 4hr session (128 GB RAM)" },
              { title: "Research Rigor", detail: "Jupyter notebooks, arXiv integration" },
              { title: "Observable AI", detail: "Journey tracking through 12D universe" },
              { title: "Open Source", detail: "Full codebase, reproducible from git clone" },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6 hover:border-cyan-500/30 transition-all"
              >
                <h3 className="text-lg font-bold mb-2 font-mono text-cyan-400">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-400">{item.detail}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Contact/Footer */}
        <footer className="border-t border-white/10 mt-24">
          <div className="max-w-6xl mx-auto px-6 py-12">
            <div className="flex flex-col md:flex-row justify-between items-center gap-8">
              <div>
                <div className="text-2xl font-bold font-mono mb-2">Let's Connect</div>
                <div className="text-gray-400 text-sm font-mono">
                  Open to Research Engineer opportunities
                </div>
              </div>

              <div className="flex gap-6">
                <a
                  href="mailto:manderson240@gmail.com"
                  className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl transition-all"
                >
                  <Mail className="w-5 h-5" />
                  <span className="font-mono text-sm">EMAIL</span>
                </a>
                <a
                  href="https://linkedin.com/in/manderson240"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl transition-all"
                >
                  <Linkedin className="w-5 h-5" />
                  <span className="font-mono text-sm">LINKEDIN</span>
                </a>
                <a
                  href="https://github.com/manderson240/cohezion"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl transition-all"
                >
                  <Github className="w-5 h-5" />
                  <span className="font-mono text-sm">GITHUB</span>
                </a>
              </div>
            </div>

            <div className="mt-12 pt-8 border-t border-white/10 text-center text-xs text-gray-600 font-mono">
              COHEZION v1.0.2 // 12D COMPOUND AI ORCHESTRATION // BUILT WITH NEXT.JS 16 + REACT 19
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
