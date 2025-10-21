import React from 'react';

interface SkeletonProps {
    className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className }) => {
    return (
        <div className={`relative overflow-hidden rounded-md bg-brand-surface ${className}`}>
            <div className="absolute inset-0 transform -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        </div>
    );
};