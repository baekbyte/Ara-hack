import { useState } from 'react'

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('')

  const submit = (e) => {
    e.preventDefault()
    onSearch(query)
  }

  const clear = () => {
    setQuery('')
    onSearch('')
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search memories…"
        style={{
          background: 'rgba(8,8,22,0.88)',
          border: '1px solid #2a2a44',
          borderRadius: 8,
          padding: '9px 16px',
          color: '#ddd',
          fontFamily: "'Courier New', monospace",
          fontSize: 13,
          width: 280,
          outline: 'none',
          backdropFilter: 'blur(8px)',
          transition: 'border-color 0.2s',
        }}
        onFocus={e => e.target.style.borderColor = '#4A9EFF66'}
        onBlur={e => e.target.style.borderColor = '#2a2a44'}
      />
      <button type="submit" style={btnStyle('#4A9EFF', '#0d1a2e')}>Search</button>
      {query && (
        <button type="button" onClick={clear} style={btnStyle('#555', '#111')}>×</button>
      )}
    </form>
  )
}

const btnStyle = (borderColor, bg) => ({
  background: bg,
  border: `1px solid ${borderColor}`,
  borderRadius: 8,
  color: borderColor,
  padding: '9px 16px',
  cursor: 'pointer',
  fontFamily: "'Courier New', monospace",
  fontSize: 13,
})
