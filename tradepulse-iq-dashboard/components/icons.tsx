import React from 'react';

// The base Icon component now accepts standard SVG props, making it more flexible.
const Icon: React.FC<React.SVGProps<SVGSVGElement>> = ({
    children,
    className,
    width = "18",
    height = "18",
    ...props
}) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={width}
        height={height}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        {...props}
    >
        {children}
    </svg>
);

// All icon components are updated to accept SVG props and pass them to the base Icon.
export const ArrowUpIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M12 5l0 14" /><path d="m18 11-6-6-6 6" /></Icon>;
export const ArrowDownIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M12 5l0 14" /><path d="m18 13-6 6-6-6" /></Icon>;
export const DollarSignIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></Icon>;
export const BarChartIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="12" x2="12" y1="20" y2="10" /><line x1="18" x2="18" y1="20" y2="4" /><line x1="6" x2="6" y1="20" y2="16" /></Icon>;
export const HashIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="4" y1="9" x2="20" y2="9" /><line x1="4" y1="15" x2="20" y2="15" /><line x1="10" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="14" y2="21" /></Icon>;
export const ActivityIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></Icon>;
export const ZapIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></Icon>;
export const PauseIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></Icon>;
export const PlayIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><polygon points="5 3 19 12 5 21 5 3" /></Icon>;
export const ChevronDownIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="m6 9 6 6 6-6" /></Icon>;
export const ChevronUpIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="m18 15-6-6-6 6" /></Icon>;
export const XIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></Icon>;
export const ListIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="8" x2="21" y1="6" y2="6"></line><line x1="8" x2="21" y1="12" y2="12"></line><line x1="8" x2="21" y1="18" y2="18"></line><line x1="3" x2="3.01" y1="6" y2="6"></line><line x1="3" x2="3.01" y1="12" y2="12"></line><line x1="3" x2="3.01" y1="18" y2="18"></line></Icon>;
export const ClockIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></Icon>;
export const TrendingUpIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></Icon>;
export const UserIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></Icon>;
export const BrandIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props} strokeWidth="1.5" viewBox="0 0 24 24"><path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" /><path d="M15.51 15.51a5 5 0 1 0 -7.02 0" /><path d="M18.36 18.36a9 9 0 1 0 -12.72 0" /></Icon>;

// --- NEW ICONS FOR AI TRAINER ---
export const LayoutDashboardIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect width="7" height="9" x="3" y="3" rx="1"></rect><rect width="7" height="5" x="14" y="3" rx="1"></rect><rect width="7" height="9" x="14" y="12" rx="1"></rect><rect width="7" height="5" x="3" y="16" rx="1"></rect></Icon>;
export const BrainCircuitIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M12 5a3 3 0 1 0-5.993.152"></path><path d="M18.668 15.65a3 3 0 1 0-4.333 4.153"></path><path d="M15 12a3 3 0 1 0-2.342 5.333"></path><path d="M17.667 9.333a3 3 0 1 0-5.332-2.343"></path><path d="M12 5h.01"></path><path d="M4.027 12.152a3 3 0 1 0 4.333 4.153"></path><path d="M9.667 9.333a3 3 0 1 0-5.332-2.343"></path><path d="M9 12a3 3 0 1 0 2.342 5.333"></path><path d="M6.332 15.65a3 3 0 1 0 4.333 4.153"></path><path d="M14.333 19.803a3 3 0 1 0 4.332-4.153"></path><path d="M9 12h6"></path><path d="m6.5 14.5-1-1"></path><path d="m18.5 9.5-1-1"></path><path d="m14.5 17.5-1 1"></path><path d="m9.5 6.5-1 1"></path><path d="m12 8-1-1"></path></Icon>;
export const CheckCircle2Icon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="m9 12 2 2 4-4"></path></Icon>;
export const XCircleIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"></circle><path d="m15 9-6 6"></path><path d="m9 9 6 6"></path></Icon>;
export const AlertTriangleIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></Icon>;
export const CpuIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect width="16" height="16" x="4" y="4" rx="2"></rect><rect width="6" height="6" x="9" y="9" rx="1"></rect><path d="M15 2v2"></path><path d="M15 20v2"></path><path d="M9 2v2"></path><path d="M9 20v2"></path><path d="M2 15h2"></path><path d="M2 9h2"></path><path d="M20 15h2"></path><path d="M20 9h2"></path></Icon>;
export const FlaskConicalIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M10 2v7.31"></path><path d="M14 9.31V2"></path><path d="M8.5 2h7"></path><path d="M14 9.31 16.59 14a2 2 0 0 1-1.79 3H9.2a2 2 0 0 1-1.79-3L10 9.31"></path><path d="M9.99 9.31h4.02"></path></Icon>;
export const ClipboardCheckIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect width="8" height="4" x="8" y="2" rx="1" ry="1"></rect><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><path d="m9 14 2 2 4-4"></path></Icon>;
export const FileTextIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" x2="8" y1="13" y2="13"></line><line x1="16" x2="8" y1="17" y2="17"></line><line x1="10" x2="8" y1="9" y2="9"></line></Icon>;
export const BarChartBigIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M3 3v18h18"></path><rect width="4" height="7" x="7" y="10" rx="1"></rect><rect width="4" height="12" x="15" y="5" rx="1"></rect></Icon>;
export const RocketIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.3.05-3.05-.64-.75-2.21-.8-3.05-.05zm9.5 4.5c1.26-1.5 5-2 5-2s-.5 3.74-2 5c-.84.71-2.3.7-3.05.05-.75-.64-.8-2.21-.05-3.05z"></path><path d="m12 15-3-3 3-3 3 3-3 3z"></path><path d="M9.5 17.5 4.5 22.5"></path><path d="M14.5 17.5 19.5 22.5"></path><path d="M12 2v2.5"></path><path d="m19.5 4.5-2 2"></path><path d="m4.5 4.5 2 2"></path></Icon>;
export const RotateCwIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path></Icon>;
export const InfoIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></Icon>;
export const ClipboardCopyIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect width="8" height="4" x="8" y="2" rx="1" ry="1"></rect><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path></Icon>;
export const SparklesIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="m12 3-1.9 4.8-4.8 1.9 4.8 1.9 1.9 4.8 1.9-4.8 4.8-1.9-4.8-1.9z"></path></Icon>;
export const ReceiptIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" /><path d="M16 8h-6a2 2 0 1 0 0 4h6" /><path d="M12 14v-4" /></Icon>;
export const TimerIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="10" x2="14" y1="2" y2="2" /><line x1="12" x2="12" y1="5" y2="9" /><circle cx="12" cy="14" r="8" /></Icon>;
export const ShuffleIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M2 18h.01" /><path d="M7 18h.01" /><path d="M12 18h.01" /><path d="M17 18h.01" /><path d="M22 18h.01" /><path d="M17 13h.01" /><path d="M22 13h.01" /><path d="M2 13h.01" /><path d="M7 13h.01" /><path d="M2 8h.01" /><path d="M7 8h.01" /><path d="M12 8h.01" /><path d="M2 3h.01" /><path d="M7 3h.01" /><path d="M12 3h.01" /><path d="M22 3h.01" /></Icon>;

// --- NEW ICONS FOR EXCHANGE SETTINGS ---
export const SettingsIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M12.22 2h-4.44l-3 3v10l3 3h10l3-3V5l-3-3h-4.44Z"/><path d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z"/><path d="M12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/></Icon>;
export const PlusIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></Icon>;
export const EditIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></Icon>;
export const TrashIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></Icon>;
export const KeyIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 11.5 3 3"/></Icon>;
export const CopyIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => <Icon {...props}><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></Icon>;