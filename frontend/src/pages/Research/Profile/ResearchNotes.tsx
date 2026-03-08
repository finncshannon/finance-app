import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import type { ResearchNote } from '../types';
import styles from './ResearchNotes.module.css';

interface ResearchNotesProps {
  ticker: string;
}

const NOTE_TYPES = ['general', 'bull', 'bear', 'risk', 'catalyst'] as const;
type NoteType = (typeof NOTE_TYPES)[number];

function badgeClass(type: string): string {
  switch (type) {
    case 'bull':
      return styles.badgeBull ?? '';
    case 'bear':
      return styles.badgeBear ?? '';
    case 'risk':
      return styles.badgeRisk ?? '';
    case 'catalyst':
      return styles.badgeCatalyst ?? '';
    default:
      return styles.badgeGeneral ?? '';
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ResearchNotes({ ticker }: ResearchNotesProps) {
  const [notes, setNotes] = useState<ResearchNote[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [newText, setNewText] = useState('');
  const [newType, setNewType] = useState<NoteType>('general');
  const [creating, setCreating] = useState(false);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await api.get<{ notes: ResearchNote[] }>(
        `/api/v1/research/${ticker}/notes`
      );
      setNotes(data.notes);
    } catch {
      /* silently fail */
    }
  }, [ticker]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleCreate = async () => {
    if (!newText.trim()) return;
    setCreating(true);
    try {
      const note = await api.post<ResearchNote>(
        `/api/v1/research/${ticker}/notes`,
        { note_text: newText.trim(), note_type: newType }
      );
      setNotes((prev) => [note, ...prev]);
      setNewText('');
      setNewType('general');
    } catch {
      /* silently fail */
    } finally {
      setCreating(false);
    }
  };

  const handleUpdate = async (id: number) => {
    if (!editText.trim()) return;
    try {
      const updated = await api.put<ResearchNote>(
        `/api/v1/research/notes/${id}`,
        { note_text: editText.trim() }
      );
      setNotes((prev) =>
        prev.map((n) => (n.id === id ? { ...n, ...updated } : n))
      );
      setEditingId(null);
      setEditText('');
    } catch {
      /* silently fail */
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this note?')) return;
    try {
      await api.del(`/api/v1/research/notes/${id}`);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch {
      /* silently fail */
    }
  };

  const startEdit = (note: ResearchNote) => {
    setEditingId(note.id);
    setEditText(note.note_text);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  return (
    <div className={styles.card ?? ''}>
      <h3 className={styles.title ?? ''}>Research Notes</h3>

      {/* Add note form */}
      <div className={styles.addForm ?? ''}>
        <textarea
          className={styles.textarea ?? ''}
          placeholder="Add a research note..."
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          rows={3}
        />
        <div className={styles.addControls ?? ''}>
          <select
            className={styles.typeSelect ?? ''}
            value={newType}
            onChange={(e) => setNewType(e.target.value as NoteType)}
          >
            {NOTE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
          <button
            className={styles.saveBtn ?? ''}
            onClick={handleCreate}
            disabled={creating || !newText.trim()}
          >
            {creating ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Notes list */}
      <div className={styles.notesList ?? ''}>
        {notes.length === 0 && (
          <p className={styles.empty ?? ''}>No notes yet</p>
        )}
        {notes.map((note) => (
          <div key={note.id} className={styles.noteCard ?? ''}>
            <div className={styles.noteHeader ?? ''}>
              <span className={badgeClass(note.note_type)}>
                {note.note_type}
              </span>
              <span className={styles.noteDate ?? ''}>
                {formatDate(note.created_at)}
              </span>
              <div className={styles.noteActions ?? ''}>
                <button
                  className={styles.actionBtn ?? ''}
                  onClick={() => startEdit(note)}
                >
                  Edit
                </button>
                <button
                  className={styles.actionBtn ?? ''}
                  onClick={() => handleDelete(note.id)}
                >
                  Delete
                </button>
              </div>
            </div>
            {editingId === note.id ? (
              <div className={styles.editArea ?? ''}>
                <textarea
                  className={styles.textarea ?? ''}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={3}
                />
                <div className={styles.editControls ?? ''}>
                  <button
                    className={styles.saveBtn ?? ''}
                    onClick={() => handleUpdate(note.id)}
                    disabled={!editText.trim()}
                  >
                    Save
                  </button>
                  <button
                    className={styles.cancelBtn ?? ''}
                    onClick={cancelEdit}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <p className={styles.noteText ?? ''}>{note.note_text}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
