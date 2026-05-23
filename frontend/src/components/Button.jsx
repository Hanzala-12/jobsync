import './Button.css'
import { Loader2 } from 'lucide-react'

const Button = ({
  children,
  variant = 'primary', // primary, secondary, danger
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) => {
  return (
    <button
      type={type}
      className={`btn btn-${variant} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {loading && <Loader2 className="btn-spinner" size={14} />}
      <span className="btn-content" style={{ opacity: loading ? 0 : 1 }}>
        {children}
      </span>
    </button>
  )
}

export default Button
