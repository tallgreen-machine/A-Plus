import React, { useState, useRef, useEffect } from 'react';
import { UserIcon, ChevronDownIcon } from './icons';

interface User {
    id: string;
    name: string;
}

interface UserSelectorProps {
    users: User[];
    selectedUser: string;
    onSelectUser: (userId: string) => void;
}

export const UserSelector: React.FC<UserSelectorProps> = ({ users, selectedUser, onSelectUser }) => {
    const [isOpen, setIsOpen] = useState(false);
    const wrapperRef = useRef<HTMLDivElement>(null);

    const selectedUserName = users.find(u => u.id === selectedUser)?.name || 'Select User';

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleSelect = (userId: string) => {
        onSelectUser(userId);
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={wrapperRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center space-x-2 bg-brand-surface/70 border border-brand-border p-2 rounded-lg hover:bg-brand-border transition-colors w-40 text-left"
            >
                <UserIcon className="w-5 h-5 text-brand-text-secondary" />
                <span className="flex-1 text-sm font-semibold text-brand-text-primary truncate">{selectedUserName}</span>
                <ChevronDownIcon className={`w-4 h-4 text-brand-text-secondary transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-40 bg-brand-surface border border-brand-border rounded-lg shadow-lg z-10 animate-fadeIn">
                    <ul className="py-1">
                        {users.map(user => (
                            <li key={user.id}>
                                <button
                                    onClick={() => handleSelect(user.id)}
                                    className={`w-full text-left px-4 py-2 text-sm ${
                                        selectedUser === user.id
                                            ? 'bg-brand-primary/20 text-brand-primary'
                                            : 'text-brand-text-primary hover:bg-brand-border'
                                    }`}
                                >
                                    {user.name}
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};
