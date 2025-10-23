import React, { useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { XIcon } from './icons';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    children: React.ReactNode;
    title: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children, title }) => {
    const modalRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        const handleClickOutside = (event: MouseEvent) => {
            if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
                onClose();
            }
        }

        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'hidden';
            // Use timeout to prevent immediate close on click that opens modal
            setTimeout(() => {
                document.addEventListener('mousedown', handleClickOutside);
            }, 0);
        }

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.removeEventListener('mousedown', handleClickOutside);
            document.body.style.overflow = 'auto';
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return ReactDOM.createPortal(
        <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            aria-labelledby="modal-title"
            role="dialog"
            aria-modal="true"
        >
            <div 
                ref={modalRef}
                className="relative bg-brand-surface w-full max-w-4xl max-h-[90vh] rounded-xl border border-brand-border shadow-2xl flex flex-col animate-fadeIn"
            >
                <header className="flex items-center justify-between p-4 border-b border-brand-border shrink-0">
                    <h2 id="modal-title" className="text-xl font-bold text-brand-text-primary">{title}</h2>
                    <button 
                        onClick={onClose}
                        className="p-2 rounded-full text-brand-text-secondary hover:bg-brand-border hover:text-brand-primary transition-colors"
                        aria-label="Close modal"
                    >
                        <XIcon className="w-5 h-5" />
                    </button>
                </header>
                <main className="flex-1 p-6 overflow-y-auto">
                    {children}
                </main>
            </div>
        </div>,
        document.body
    );
};
