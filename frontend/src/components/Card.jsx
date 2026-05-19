import './Card.css'

const Card = ({ children, className = '', title, action, ...props }) => {
  return (
    <div className={`card ${className}`.trim()} {...props}>
      {(title || action) && (
        <div className="card-header">
          {title && <h2 className="card-title">{title}</h2>}
          {action && <div className="card-action">{action}</div>}
        </div>
      )}
      <div className="card-content">{children}</div>
    </div>
  )
}

export default Card
