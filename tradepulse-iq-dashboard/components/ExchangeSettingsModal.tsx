import React, { useState, useEffect, FormEvent } from 'react';
import { Modal } from './Modal';
import * as api from '../services/realApi';
import type { ExchangeConnection } from '../types';
import { SparklesIcon } from './icons';

interface ExchangeSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: () => void;
    connection: ExchangeConnection | null;
    currentUser: string;
}

const supportedExchanges: ExchangeConnection['exchangeName'][] = ['Binance', 'Coinbase', 'Bybit', 'Kraken', 'OKX', 'KuCoin'];

export const ExchangeSettingsModal: React.FC<ExchangeSettingsModalProps> = ({ isOpen, onClose, onSave, connection, currentUser }) => {
    const [formData, setFormData] = useState({
        exchangeName: 'Binance' as ExchangeConnection['exchangeName'],
        nickname: '',
        apiKey: '',
        apiSecret: ''
    });
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (isOpen) {
            if (connection) {
                setFormData({
                    exchangeName: connection.exchangeName,
                    nickname: connection.nickname,
                    apiKey: connection.apiKey,
                    apiSecret: connection.apiSecret,
                });
            } else {
                 setFormData({
                    exchangeName: 'Binance',
                    nickname: '',
                    apiKey: '',
                    apiSecret: ''
                });
            }
            setError('');
            setIsSaving(false);
        }
    }, [isOpen, connection]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        
        if (!formData.nickname || !formData.apiKey || !formData.apiSecret) {
            setError('All fields are required.');
            return;
        }

        setIsSaving(true);
        try {
            await api.saveExchangeConnection(currentUser, { ...formData, id: connection?.id });
            onSave();
        } catch (err) {
            setError('Failed to save connection. Please try again.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Modal 
            isOpen={isOpen} 
            onClose={onClose} 
            title={connection ? 'Edit Exchange Connection' : 'Add Exchange Connection'}
        >
            <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                    <label htmlFor="exchangeName" className="block text-sm font-medium text-brand-text-secondary">
                        Exchange
                    </label>
                    <select
                        id="exchangeName"
                        name="exchangeName"
                        value={formData.exchangeName}
                        onChange={handleChange}
                        className="mt-1 block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm"
                    >
                        {supportedExchanges.map(ex => (
                            <option key={ex} value={ex}>{ex}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label htmlFor="nickname" className="block text-sm font-medium text-brand-text-secondary">
                        Nickname
                    </label>
                    <input
                        type="text"
                        id="nickname"
                        name="nickname"
                        value={formData.nickname}
                        onChange={handleChange}
                        placeholder="e.g., Main Trading Account"
                        className="mt-1 block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm"
                    />
                </div>

                <div>
                    <label htmlFor="apiKey" className="block text-sm font-medium text-brand-text-secondary">
                        API Key
                    </label>
                    <input
                        type="text"
                        id="apiKey"
                        name="apiKey"
                        value={formData.apiKey}
                        onChange={handleChange}
                        placeholder="Enter your API key"
                        className="mt-1 block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm"
                    />
                </div>

                <div>
                    <label htmlFor="apiSecret" className="block text-sm font-medium text-brand-text-secondary">
                        API Secret
                    </label>
                    <input
                        type="password"
                        id="apiSecret"
                        name="apiSecret"
                        value={formData.apiSecret}
                        onChange={handleChange}
                        placeholder="Enter your API secret"
                        className="mt-1 block w-full bg-brand-bg border border-brand-border rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand-primary focus:border-brand-primary sm:text-sm"
                    />
                </div>
                
                {error && <p className="text-sm text-brand-negative">{error}</p>}

                <div className="pt-4 flex justify-end gap-3">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isSaving}
                        className="bg-brand-border text-brand-text-primary font-semibold px-4 py-2 rounded-lg hover:bg-brand-border/70 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={isSaving}
                        className="flex items-center justify-center gap-2 bg-brand-primary text-white font-semibold px-4 py-2 rounded-lg hover:bg-brand-primary/80 transition-colors disabled:bg-brand-border disabled:text-brand-text-secondary disabled:cursor-not-allowed"
                    >
                        {isSaving ? (
                            <>
                                <SparklesIcon className="w-4 h-4 animate-pulse" />
                                <span>Testing & Saving...</span>
                            </>
                        ) : (
                            <span>Save & Test Connection</span>
                        )}
                    </button>
                </div>
            </form>
        </Modal>
    );
};
