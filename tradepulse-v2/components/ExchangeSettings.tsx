import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../services/realApi';
import type { ExchangeConnection } from '../types';
import { ExchangeConnectionStatus } from '../types';
import { Skeleton } from './Skeleton';
import { PlusIcon, EditIcon, TrashIcon, KeyIcon } from './icons';
import { ExchangeSettingsModal } from './ExchangeSettingsModal';

interface ExchangeSettingsProps {
    currentUser: string;
}

const ConnectionCard: React.FC<{
    connection: ExchangeConnection;
    onEdit: () => void;
    onDelete: () => void;
}> = ({ connection, onEdit, onDelete }) => {
    const isConnected = connection.status === ExchangeConnectionStatus.CONNECTED;
    
    const maskString = (str: string) => {
        if (str.length <= 8) return '********';
        return `${str.substring(0, 4)}...${str.substring(str.length - 4)}`;
    }

    return (
        <div className="bg-brand-surface border border-brand-border rounded-lg p-4 flex flex-col gap-4 animate-fadeIn">
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="text-lg font-bold text-brand-text-primary">{connection.nickname}</h3>
                    <p className="text-sm text-brand-text-secondary">{connection.exchangeName}</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-brand-positive' : 'bg-brand-negative'}`}></div>
                    <span className={`text-sm font-semibold ${isConnected ? 'text-brand-positive' : 'text-brand-negative'}`}>
                        {isConnected ? 'Connected' : 'Error'}
                    </span>
                </div>
            </div>
            <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                    <KeyIcon className="w-4 h-4 text-brand-text-secondary" />
                    <span className="text-brand-text-secondary">API Key:</span>
                    <span className="font-mono text-brand-text-primary">{maskString(connection.apiKey)}</span>
                </div>
                 <div className="flex items-center gap-2">
                    <KeyIcon className="w-4 h-4 text-brand-text-secondary" />
                    <span className="text-brand-text-secondary">API Secret:</span>
                    <span className="font-mono text-brand-text-primary">********************</span>
                </div>
            </div>
            <div className="mt-auto pt-4 flex gap-2">
                <button onClick={onEdit} className="flex-1 flex items-center justify-center gap-2 text-sm bg-brand-border text-brand-text-secondary font-semibold px-3 py-2 rounded-md hover:bg-brand-border/70 transition-colors">
                    <EditIcon className="w-4 h-4" />
                    <span>Edit</span>
                </button>
                 <button onClick={onDelete} className="flex-1 flex items-center justify-center gap-2 text-sm bg-brand-negative/10 text-brand-negative font-semibold px-3 py-2 rounded-md hover:bg-brand-negative/20 transition-colors">
                     <TrashIcon className="w-4 h-4" />
                    <span>Delete</span>
                </button>
            </div>
        </div>
    );
};

export const ExchangeSettings: React.FC<ExchangeSettingsProps> = ({ currentUser }) => {
    const [connections, setConnections] = useState<ExchangeConnection[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedConnection, setSelectedConnection] = useState<ExchangeConnection | null>(null);

    const fetchConnections = useCallback(async () => {
        setLoading(true);
        const data = await api.getExchangeConnections(currentUser);
        setConnections(data);
        setLoading(false);
    }, [currentUser]);

    useEffect(() => {
        fetchConnections();
    }, [fetchConnections]);

    const handleAdd = () => {
        setSelectedConnection(null);
        setIsModalOpen(true);
    };

    const handleEdit = (connection: ExchangeConnection) => {
        setSelectedConnection(connection);
        setIsModalOpen(true);
    };

    const handleDelete = async (connectionId: string) => {
        if (window.confirm('Are you sure you want to delete this exchange connection?')) {
            await api.deleteExchangeConnection(currentUser, connectionId);
            await fetchConnections();
        }
    };
    
    const handleSave = async () => {
        setIsModalOpen(false);
        await fetchConnections();
    }

    if (loading) {
        return (
            <div className="p-4 lg:p-6">
                <Skeleton className="h-10 w-64 mb-6" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-48" />)}
                </div>
            </div>
        )
    }

    return (
        <div className="p-4 lg:p-6 space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-brand-text-primary">Exchange Settings</h1>
                    <p className="text-brand-text-secondary mt-1">Manage your API keys and connections to trading exchanges.</p>
                </div>
                <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors"
                >
                    <PlusIcon className="w-4 h-4" />
                    <span>Add Connection</span>
                </button>
            </header>
            
            <main>
                {connections.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {connections.map(conn => (
                            <ConnectionCard
                                key={conn.id}
                                connection={conn}
                                onEdit={() => handleEdit(conn)}
                                onDelete={() => handleDelete(conn.id)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-16 bg-brand-surface rounded-lg border border-dashed border-brand-border">
                        <h3 className="text-xl font-semibold">No Connections Found</h3>
                        <p className="text-brand-text-secondary mt-2">Get started by adding your first exchange API connection.</p>
                         <button
                            onClick={handleAdd}
                            className="mt-6 flex items-center mx-auto gap-2 bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors"
                        >
                            <PlusIcon className="w-4 h-4" />
                            <span>Add New Connection</span>
                        </button>
                    </div>
                )}
            </main>

            <ExchangeSettingsModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleSave}
                connection={selectedConnection}
                currentUser={currentUser}
            />
        </div>
    );
};
