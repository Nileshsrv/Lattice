import type { ReactNode } from "react";

function Icon(props: { children: ReactNode; size?: number }) {
  const size = props.size ?? 16;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {props.children}
    </svg>
  );
}

export function LogoMark(props: { size?: number }) {
  const size = props.size ?? 26;
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="lattice-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5aa9ff" />
          <stop offset="1" stopColor="#9085e9" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#lattice-logo)" />
      <g stroke="rgba(255,255,255,0.55)" strokeWidth="1.3">
        <path d="M10 10L22 22M22 10L10 22M10 10H22V22H10Z" fill="none" />
      </g>
      <g fill="#fff">
        <circle cx="10" cy="10" r="2.5" />
        <circle cx="22" cy="10" r="2.5" />
        <circle cx="10" cy="22" r="2.5" />
        <circle cx="22" cy="22" r="2.5" />
        <circle cx="16" cy="16" r="2.5" />
      </g>
    </svg>
  );
}

export const IconProjects = () => (
  <Icon>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <rect x="14" y="14" width="7" height="7" rx="1.5" />
  </Icon>
);
export const IconOverview = () => (
  <Icon>
    <path d="M3 11l9-7 9 7" />
    <path d="M5 10v10h14V10" />
  </Icon>
);
export const IconData = () => (
  <Icon>
    <ellipse cx="12" cy="6" rx="8" ry="3" />
    <path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6" />
    <path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
  </Icon>
);
export const IconTools = () => (
  <Icon>
    <path d="M9 3h6" />
    <path d="M10 3v6l-5.2 9a2 2 0 001.7 3h11a2 2 0 001.7-3L14 9V3" />
    <path d="M7.5 15h9" />
  </Icon>
);
export const IconRuns = () => (
  <Icon>
    <path d="M3 17l5-6 4 4 8-10" />
    <path d="M15 5h5v5" />
  </Icon>
);
export const IconNotebook = () => (
  <Icon>
    <path d="M6 3h12a1 1 0 011 1v16a1 1 0 01-1 1H6z" />
    <path d="M6 3v18M10 8h5M10 12h5" />
  </Icon>
);
export const IconActivity = () => (
  <Icon>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Icon>
);
export const IconLibrary = () => (
  <Icon>
    <path d="M4 4v16M9 4v16M14 5l5 15" />
  </Icon>
);
export const IconBack = () => (
  <Icon>
    <path d="M15 5l-7 7 7 7" />
  </Icon>
);
export const IconSun = () => (
  <Icon>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M5 19l1.4-1.4M17.6 6.4L19 5" />
  </Icon>
);
export const IconMoon = () => (
  <Icon>
    <path d="M20 14.5A8 8 0 019.5 4 8 8 0 1020 14.5z" />
  </Icon>
);
export const IconSpark = () => (
  <Icon>
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
    <path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
  </Icon>
);
export const IconLink = () => (
  <Icon size={18}>
    <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.700-5.700l-1 1" />
    <path d="M14 10a4 4 0 00-5.700 0l-3 3a4 4 0 005.700 5.700l1-1" />
  </Icon>
);
export const IconShield = () => (
  <Icon size={18}>
    <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.800-1-8-4.500-8-9V6z" />
    <path d="M9 12l2 2 4-4" />
  </Icon>
);
export const IconUsers = () => (
  <Icon size={18}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.500 20a6.500 6.500 0 0113 0" />
    <circle cx="17.500" cy="9" r="2.500" />
    <path d="M17 14.500a5 5 0 014.500 5" />
  </Icon>
);

export function initials(name: string): string {
  const parts = name.split(/[\s_.-]+/).filter(Boolean);
  const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
  return letters.toUpperCase();
}
