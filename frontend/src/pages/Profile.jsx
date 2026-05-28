import { useEffect, useMemo, useState } from 'react'
import { profileAPI } from '../api/client'
import Button from '../components/Button'
import {
  BadgeCheck,
  Briefcase,
  CheckCircle2,
  FolderKanban,
  GraduationCap,
  Languages,
  LayoutGrid,
  PencilLine,
  Plus,
  Settings2,
  Sparkles,
  Trash2,
  UserCircle,
} from 'lucide-react'
import './Profile.css'

const tabs = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'education', label: 'Education', icon: GraduationCap },
  { id: 'experience', label: 'Experience', icon: Briefcase },
  { id: 'skills', label: 'Skills', icon: Sparkles },
  { id: 'credentials', label: 'Credentials', icon: BadgeCheck },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'languages', label: 'Languages', icon: Languages },
  { id: 'preferences', label: 'Preferences', icon: Settings2 },
]

const blankEducation = () => ({ degree: '', institution: '', field_of_study: '', start_year: '', end_year: '', gpa: '', description: '' })
const blankExperience = () => ({ job_title: '', company: '', location: '', start_date: '', end_date: '', responsibilities: [''], achievements: [''] })
const blankCertification = () => ({ name: '', issuing_org: '', date_earned: '', credential_url: '' })
const blankProject = () => ({ name: '', description: '', technologies: [''], project_url: '' })
const blankLanguage = () => ({ name: '', proficiency: '' })

const createEmptyProfile = () => ({
  full_name: '',
  email: '',
  phone: '',
  location: '',
  linkedin_url: '',
  portfolio_url: '',
  summary: '',
  skills: [],
  achievements: [],
  preferred_job_titles: [],
  desired_salary_min: '',
  desired_salary_max: '',
  willing_to_relocate: false,
  preferred_work_location: '',
  resume_text: '',
  education: [blankEducation()],
  work_experience: [blankExperience()],
  certifications: [blankCertification()],
  projects: [blankProject()],
  languages: [blankLanguage()],
})

const listToText = (value) => (Array.isArray(value) ? value.filter(Boolean).join(', ') : '')
const textToList = (value) =>
  String(value || '')
    .split(/[\n,;|]+/)
    .map((item) => item.trim())
    .filter(Boolean)

const normalizeEntries = (entries, blankFactory) => {
  const mapped = (Array.isArray(entries) ? entries : []).map((entry) => ({ ...blankFactory(), ...entry }))
  return mapped.length > 0 ? mapped : [blankFactory()]
}

const calculateCompleteness = (profile) => {
  const checks = [
    profile.full_name,
    profile.email,
    profile.phone,
    profile.location,
    profile.summary,
    profile.skills?.length,
    profile.achievements?.length,
    profile.preferred_job_titles?.length,
    profile.education?.some((item) => item.degree || item.institution || item.field_of_study),
    profile.work_experience?.some((item) => item.job_title || item.company),
    profile.certifications?.some((item) => item.name || item.issuing_org),
    profile.projects?.some((item) => item.name || item.description),
    profile.languages?.some((item) => item.name || item.proficiency),
    profile.desired_salary_min || profile.desired_salary_max,
    profile.preferred_work_location,
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
}

function Field({ label, children, hint }) {
  return (
    <label className="profile-field">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  )
}

function ArrayField({ label, value, onChange, placeholder, hint }) {
  return (
    <Field label={label} hint={hint}>
      <textarea
        className="field-input field-textarea"
        rows={4}
        value={listToText(value)}
        onChange={(event) => onChange(textToList(event.target.value))}
        placeholder={placeholder}
      />
    </Field>
  )
}

function SectionHeader({ icon: Icon, title, description, onAdd, addLabel }) {
  return (
    <div className="section-header">
      <div>
        <div className="section-kicker">
          <Icon size={16} />
          {title}
        </div>
        {description ? <p className="section-description">{description}</p> : null}
      </div>
      {onAdd ? (
        <button type="button" className="ghost-button" onClick={onAdd}>
          <Plus size={14} />
          {addLabel || 'Add'}
        </button>
      ) : null}
    </div>
  )
}

function ItemCard({ index, onRemove, children, title }) {
  return (
    <div className="item-card">
      <div className="item-card-header">
        <div className="item-card-title">{title} {index + 1}</div>
        <button type="button" className="icon-button danger" onClick={onRemove} aria-label={`Remove ${title.toLowerCase()} ${index + 1}`}>
          <Trash2 size={14} />
        </button>
      </div>
      {children}
    </div>
  )
}

export default function Profile() {
  const [activeTab, setActiveTab] = useState('overview')
  const [form, setForm] = useState(createEmptyProfile)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [profiles, setProfiles] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [editingProfileId, setEditingProfileId] = useState(null)
  const [selectedProfile, setSelectedProfile] = useState(null)
  const [pageIndex, setPageIndex] = useState(1)
  const [pageSize] = useState(4)
  const [totalProfiles, setTotalProfiles] = useState(0)

  const completeness = useMemo(() => calculateCompleteness(form), [form])

  const patchForm = (patch) => setForm((current) => ({ ...current, ...patch }))
  const updateListField = (field, value) => patchForm({ [field]: value })

  const updateEntry = (field, index, key, value) => {
    setForm((current) => {
      const next = [...current[field]]
      next[index] = { ...next[index], [key]: value }
      return { ...current, [field]: next }
    })
  }

  const addEntry = (field, blankFactory) => {
    setForm((current) => ({ ...current, [field]: [...current[field], blankFactory()] }))
  }

  const removeEntry = (field, index, blankFactory) => {
    setForm((current) => {
      const next = current[field].filter((_, itemIndex) => itemIndex !== index)
      return { ...current, [field]: next.length ? next : [blankFactory()] }
    })
  }

  const resetForm = () => {
    setEditingProfileId(null)
    setForm(createEmptyProfile())
    setActiveTab('overview')
    setMessage('')
  }

  const loadProfiles = async () => {
    try {
      const res = await profileAPI.list(pageIndex, pageSize)
      const data = res.data || {}
      setProfiles(data.profiles || [])
      setSelectedId(data.selected_profile_id || null)
      setTotalProfiles(data.total || 0)
      setSelectedProfile(data.selected_profile || null)
    } catch (error) {
      setProfiles([])
    }
  }

  useEffect(() => {
    loadProfiles()
  }, [pageIndex])

  useEffect(() => {
    if (!selectedId) {
      setSelectedProfile(null)
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const res = await profileAPI.get(selectedId)
        if (mounted) setSelectedProfile(res.data || null)
      } catch (error) {
        if (mounted) setSelectedProfile(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [selectedId])

  const loadProfileIntoForm = async (profileId) => {
    try {
      const res = await profileAPI.get(profileId)
      const data = res.data || {}
      setForm({
        full_name: data.full_name || '',
        email: data.email || '',
        phone: data.phone || '',
        location: data.location || '',
        linkedin_url: data.linkedin_url || '',
        portfolio_url: data.portfolio_url || '',
        summary: data.summary || '',
        skills: data.skills || [],
        achievements: data.achievements || [],
        preferred_job_titles: data.preferred_job_titles || [],
        desired_salary_min: data.desired_salary_min ?? '',
        desired_salary_max: data.desired_salary_max ?? '',
        willing_to_relocate: Boolean(data.willing_to_relocate),
        preferred_work_location: data.preferred_work_location || '',
        resume_text: data.resume_text || '',
        education: normalizeEntries(data.education, blankEducation),
        work_experience: normalizeEntries(data.work_experience, blankExperience),
        certifications: normalizeEntries(data.certifications, blankCertification),
        projects: normalizeEntries(data.projects, blankProject),
        languages: normalizeEntries(data.languages, blankLanguage),
      })
      setEditingProfileId(profileId)
      setMessage('Loaded profile for editing')
      setActiveTab('overview')
    } catch (error) {
      setMessage('Failed to load profile details')
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    const payload = {
      ...form,
      skills: textToList(listToText(form.skills)),
      achievements: textToList(listToText(form.achievements)),
      preferred_job_titles: textToList(listToText(form.preferred_job_titles)),
      desired_salary_min: form.desired_salary_min === '' ? null : Number(form.desired_salary_min),
      desired_salary_max: form.desired_salary_max === '' ? null : Number(form.desired_salary_max),
      education: form.education.map((item) => ({
        degree: item.degree || '',
        institution: item.institution || '',
        field_of_study: item.field_of_study || '',
        start_year: item.start_year === '' ? null : Number(item.start_year),
        end_year: item.end_year === '' ? null : Number(item.end_year),
        gpa: item.gpa || '',
        description: item.description || '',
      })),
      work_experience: form.work_experience.map((item) => ({
        job_title: item.job_title || '',
        company: item.company || '',
        location: item.location || '',
        start_date: item.start_date || '',
        end_date: item.end_date || '',
        responsibilities: textToList(listToText(item.responsibilities)),
        achievements: textToList(listToText(item.achievements)),
      })),
      certifications: form.certifications.map((item) => ({
        name: item.name || '',
        issuing_org: item.issuing_org || '',
        date_earned: item.date_earned || '',
        credential_url: item.credential_url || '',
      })),
      projects: form.projects.map((item) => ({
        name: item.name || '',
        description: item.description || '',
        technologies: textToList(listToText(item.technologies)),
        project_url: item.project_url || '',
      })),
      languages: form.languages.map((item) => ({
        name: item.name || '',
        proficiency: item.proficiency || '',
      })),
    }

    try {
      const response = editingProfileId
        ? await profileAPI.update(editingProfileId, payload)
        : await profileAPI.create(payload)

      setMessage(response.data?.message || (editingProfileId ? 'Profile updated successfully' : 'Profile created successfully'))
      const savedProfile = response.data?.profile
      if (savedProfile?.id) {
        setSelectedId(savedProfile.id)
        try {
          await profileAPI.select(savedProfile.id)
        } catch (error) {
          // selection is best-effort
        }
      }
      await loadProfiles()
      if (!editingProfileId) {
        resetForm()
      }
    } catch (error) {
      setMessage('Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = async (id) => {
    try {
      await profileAPI.select(id)
      setSelectedId(id)
      setMessage('Active profile updated')
    } catch (error) {
      setMessage('Failed to set active profile')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this profile permanently?')) return
    try {
      await profileAPI.delete(id)
      if (selectedId === id) {
        setSelectedId(null)
        setSelectedProfile(null)
      }
      if (editingProfileId === id) {
        resetForm()
      }
      setMessage('Profile deleted')
      await loadProfiles()
    } catch (error) {
      setMessage('Failed to delete profile')
    }
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="profile-section-grid">
            <Field label="Full Name"><input className="field-input" value={form.full_name} onChange={(event) => patchForm({ full_name: event.target.value })} placeholder="Your full name" /></Field>
            <Field label="Email"><input className="field-input" type="email" value={form.email} onChange={(event) => patchForm({ email: event.target.value })} placeholder="you@example.com" /></Field>
            <Field label="Phone"><input className="field-input" value={form.phone} onChange={(event) => patchForm({ phone: event.target.value })} placeholder="+92..." /></Field>
            <Field label="Location"><input className="field-input" value={form.location} onChange={(event) => patchForm({ location: event.target.value })} placeholder="City, Country" /></Field>
            <Field label="LinkedIn URL"><input className="field-input" value={form.linkedin_url} onChange={(event) => patchForm({ linkedin_url: event.target.value })} placeholder="https://linkedin.com/in/..." /></Field>
            <Field label="Portfolio URL"><input className="field-input" value={form.portfolio_url} onChange={(event) => patchForm({ portfolio_url: event.target.value })} placeholder="https://..." /></Field>
            <Field label="Summary" hint="A concise professional snapshot"><textarea className="field-input field-textarea" rows={5} value={form.summary} onChange={(event) => patchForm({ summary: event.target.value })} placeholder="Write a short profile summary..." /></Field>
          </div>
        )
      case 'education':
        return (
          <div className="stacked-section">
            <SectionHeader icon={GraduationCap} title="Education" description="Add degrees, institutions, and academic details." onAdd={() => addEntry('education', blankEducation)} addLabel="Add Education" />
            {form.education.map((item, index) => (
              <ItemCard key={index} index={index} title="Education" onRemove={() => removeEntry('education', index, blankEducation)}>
                <div className="profile-section-grid">
                  <Field label="Degree"><input className="field-input" value={item.degree} onChange={(event) => updateEntry('education', index, 'degree', event.target.value)} placeholder="BS Computer Science" /></Field>
                  <Field label="Institution"><input className="field-input" value={item.institution} onChange={(event) => updateEntry('education', index, 'institution', event.target.value)} placeholder="University name" /></Field>
                  <Field label="Field of Study"><input className="field-input" value={item.field_of_study} onChange={(event) => updateEntry('education', index, 'field_of_study', event.target.value)} placeholder="Software Engineering" /></Field>
                  <Field label="GPA"><input className="field-input" value={item.gpa} onChange={(event) => updateEntry('education', index, 'gpa', event.target.value)} placeholder="3.8" /></Field>
                  <Field label="Start Year"><input className="field-input" type="number" value={item.start_year} onChange={(event) => updateEntry('education', index, 'start_year', event.target.value)} /></Field>
                  <Field label="End Year"><input className="field-input" type="number" value={item.end_year} onChange={(event) => updateEntry('education', index, 'end_year', event.target.value)} /></Field>
                  <Field label="Notes"><textarea className="field-input field-textarea" rows={3} value={item.description} onChange={(event) => updateEntry('education', index, 'description', event.target.value)} placeholder="Honors, thesis, special projects..." /></Field>
                </div>
              </ItemCard>
            ))}
          </div>
        )
      case 'experience':
        return (
          <div className="stacked-section">
            <SectionHeader icon={Briefcase} title="Work Experience" description="Highlight measurable impact, not just responsibilities." onAdd={() => addEntry('work_experience', blankExperience)} addLabel="Add Role" />
            {form.work_experience.map((item, index) => (
              <ItemCard key={index} index={index} title="Role" onRemove={() => removeEntry('work_experience', index, blankExperience)}>
                <div className="profile-section-grid">
                  <Field label="Job Title"><input className="field-input" value={item.job_title} onChange={(event) => updateEntry('work_experience', index, 'job_title', event.target.value)} placeholder="Software Engineer" /></Field>
                  <Field label="Company"><input className="field-input" value={item.company} onChange={(event) => updateEntry('work_experience', index, 'company', event.target.value)} placeholder="Company name" /></Field>
                  <Field label="Location"><input className="field-input" value={item.location} onChange={(event) => updateEntry('work_experience', index, 'location', event.target.value)} placeholder="Remote / City" /></Field>
                  <Field label="Start Date"><input className="field-input" value={item.start_date} onChange={(event) => updateEntry('work_experience', index, 'start_date', event.target.value)} placeholder="2022-01" /></Field>
                  <Field label="End Date"><input className="field-input" value={item.end_date} onChange={(event) => updateEntry('work_experience', index, 'end_date', event.target.value)} placeholder="Present" /></Field>
                  <ArrayField label="Responsibilities" value={item.responsibilities} onChange={(next) => updateEntry('work_experience', index, 'responsibilities', next)} placeholder="Own feature delivery, debug production issues, collaborate with designers..." />
                  <ArrayField label="Achievements" value={item.achievements} onChange={(next) => updateEntry('work_experience', index, 'achievements', next)} placeholder="Reduced build time by 30%, shipped weekly releases..." />
                </div>
              </ItemCard>
            ))}
          </div>
        )
      case 'skills':
        return (
          <div className="stacked-section">
            <SectionHeader icon={Sparkles} title="Skills & Achievements" description="Keep skills as short, searchable lists." />
            <ArrayField label="Skills" value={form.skills} onChange={(next) => updateListField('skills', next)} placeholder="React, FastAPI, SQL, AWS" />
            <ArrayField label="Achievements" value={form.achievements} onChange={(next) => updateListField('achievements', next)} placeholder="Shipped onboarding flow, led migration, improved ATS score..." />
          </div>
        )
      case 'credentials':
        return (
          <div className="stacked-section">
            <SectionHeader icon={BadgeCheck} title="Certifications" description="Add certificates, licenses, and verified credentials." onAdd={() => addEntry('certifications', blankCertification)} addLabel="Add Certification" />
            {form.certifications.map((item, index) => (
              <ItemCard key={index} index={index} title="Certification" onRemove={() => removeEntry('certifications', index, blankCertification)}>
                <div className="profile-section-grid">
                  <Field label="Name"><input className="field-input" value={item.name} onChange={(event) => updateEntry('certifications', index, 'name', event.target.value)} placeholder="AWS Certified Developer" /></Field>
                  <Field label="Issuing Organization"><input className="field-input" value={item.issuing_org} onChange={(event) => updateEntry('certifications', index, 'issuing_org', event.target.value)} placeholder="AWS" /></Field>
                  <Field label="Date Earned"><input className="field-input" value={item.date_earned} onChange={(event) => updateEntry('certifications', index, 'date_earned', event.target.value)} placeholder="2024-06" /></Field>
                  <Field label="Credential URL"><input className="field-input" value={item.credential_url} onChange={(event) => updateEntry('certifications', index, 'credential_url', event.target.value)} placeholder="https://..." /></Field>
                </div>
              </ItemCard>
            ))}
          </div>
        )
      case 'projects':
        return (
          <div className="stacked-section">
            <SectionHeader icon={FolderKanban} title="Projects" description="Showcase work that maps directly to the jobs you want." onAdd={() => addEntry('projects', blankProject)} addLabel="Add Project" />
            {form.projects.map((item, index) => (
              <ItemCard key={index} index={index} title="Project" onRemove={() => removeEntry('projects', index, blankProject)}>
                <div className="profile-section-grid">
                  <Field label="Name"><input className="field-input" value={item.name} onChange={(event) => updateEntry('projects', index, 'name', event.target.value)} placeholder="Portfolio site" /></Field>
                  <Field label="Project URL"><input className="field-input" value={item.project_url} onChange={(event) => updateEntry('projects', index, 'project_url', event.target.value)} placeholder="https://..." /></Field>
                  <Field label="Technologies"><textarea className="field-input field-textarea" rows={3} value={listToText(item.technologies)} onChange={(event) => updateEntry('projects', index, 'technologies', textToList(event.target.value))} placeholder="React, Node.js, PostgreSQL" /></Field>
                  <Field label="Description"><textarea className="field-input field-textarea" rows={4} value={item.description} onChange={(event) => updateEntry('projects', index, 'description', event.target.value)} placeholder="What did the project do? What changed?" /></Field>
                </div>
              </ItemCard>
            ))}
          </div>
        )
      case 'languages':
        return (
          <div className="stacked-section">
            <SectionHeader icon={Languages} title="Languages" description="Keep language proficiency visible for recruiters." onAdd={() => addEntry('languages', blankLanguage)} addLabel="Add Language" />
            {form.languages.map((item, index) => (
              <ItemCard key={index} index={index} title="Language" onRemove={() => removeEntry('languages', index, blankLanguage)}>
                <div className="profile-section-grid single-line-grid">
                  <Field label="Language"><input className="field-input" value={item.name} onChange={(event) => updateEntry('languages', index, 'name', event.target.value)} placeholder="English" /></Field>
                  <Field label="Proficiency"><input className="field-input" value={item.proficiency} onChange={(event) => updateEntry('languages', index, 'proficiency', event.target.value)} placeholder="Native / Fluent / Intermediate" /></Field>
                </div>
              </ItemCard>
            ))}
          </div>
        )
      case 'preferences':
        return (
          <div className="profile-section-grid">
            <ArrayField label="Preferred Job Titles" value={form.preferred_job_titles} onChange={(next) => updateListField('preferred_job_titles', next)} placeholder="Backend Engineer, Data Analyst, Product Engineer" />
            <Field label="Preferred Work Location">
              <select className="field-input" value={form.preferred_work_location} onChange={(event) => patchForm({ preferred_work_location: event.target.value })}>
                <option value="">Select a preference</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </Field>
            <Field label="Minimum Salary"><input className="field-input" type="number" min="0" value={form.desired_salary_min} onChange={(event) => patchForm({ desired_salary_min: event.target.value })} placeholder="100000" /></Field>
            <Field label="Maximum Salary"><input className="field-input" type="number" min="0" value={form.desired_salary_max} onChange={(event) => patchForm({ desired_salary_max: event.target.value })} placeholder="250000" /></Field>
            <Field label="Willing to Relocate">
              <label className="checkbox-row">
                <input type="checkbox" checked={form.willing_to_relocate} onChange={(event) => patchForm({ willing_to_relocate: event.target.checked })} />
                <span>Open to roles outside my current location</span>
              </label>
            </Field>
            <Field label="Resume Notes" hint="Optional raw resume text or notes">
              <textarea className="field-input field-textarea" rows={5} value={form.resume_text} onChange={(event) => patchForm({ resume_text: event.target.value })} placeholder="Optional text that should travel with the profile..." />
            </Field>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="profile-page fade-up">
      <div className="profile-hero">
        <div>
          <div className="eyebrow">Structured Profile</div>
          <h1>My Profile</h1>
          <p className="subtitle">Capture your education, work history, credentials, and preferences in one profile that powers search and resume generation.</p>
        </div>
        <div className="completeness-card">
          <div className="completeness-label">Profile completeness</div>
          <div className="completeness-meter"><span style={{ width: `${completeness}%` }} /></div>
          <div className="completeness-value">{completeness}% complete</div>
        </div>
      </div>

      <div className="profile-layout structured-layout">
        <form className="profile-card editor-card fade-up" onSubmit={submit}>
          <div className="card-heading">
            <div>
              <h3>{editingProfileId ? 'Edit Profile' : 'Create Profile'}</h3>
              <p>Use the sections below to keep your profile structured and ATS-friendly.</p>
            </div>
            {message ? <div className="status-msg inline-msg">{message}</div> : null}
          </div>

          <div className="tab-strip" role="tablist" aria-label="Profile sections">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const active = activeTab === tab.id
              return (
                <button key={tab.id} type="button" className={`tab-pill ${active ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)} role="tab" aria-selected={active}>
                  <Icon size={14} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          <div className="tab-panel">{renderTabContent()}</div>

          <div className="form-actions sticky-actions">
            <Button type="submit" loading={loading}>{editingProfileId ? 'Update Profile' : 'Save Profile'}</Button>
            {editingProfileId ? <Button type="button" variant="secondary" onClick={resetForm}>Cancel Edit</Button> : null}
          </div>
        </form>

        <div className="side-column">
          <div className="profile-card summary-card fade-up">
            <div className="summary-head">
              <div>
                <div className="eyebrow">Active Profile</div>
                <h3>{selectedProfile?.full_name || 'No active profile'}</h3>
              </div>
              {selectedProfile?.profile_completeness ? <span className="sp-badge">{selectedProfile.profile_completeness}%</span> : null}
            </div>
            {selectedProfile ? (
              <div className="summary-stack">
                <p>{selectedProfile.summary || 'Add a summary to quickly introduce your background.'}</p>
                <div className="summary-grid">
                  <div><span>Email</span><strong>{selectedProfile.email || 'Not provided'}</strong></div>
                  <div><span>Location</span><strong>{selectedProfile.location || 'Not provided'}</strong></div>
                  <div><span>Skills</span><strong>{(selectedProfile.skills || []).length || 0}</strong></div>
                  <div><span>Projects</span><strong>{(selectedProfile.projects || []).length || 0}</strong></div>
                </div>
              </div>
            ) : (
              <p className="status-msg">Select a profile from the list to make it active.</p>
            )}
          </div>

          <div className="profile-card fade-up">
            <div className="card-heading compact">
              <div>
                <h3>Saved Profiles</h3>
                <p>Pick an active profile, edit it, or delete it.</p>
              </div>
            </div>

            <div className="saved-profiles-list">
              {profiles.length === 0 ? (
                <p className="status-msg">No profiles saved yet. Create one to get started.</p>
              ) : (
                profiles.map((item) => (
                  <div key={item.id} className={`saved-profile-card ${selectedId === item.id ? 'active' : ''}`}>
                    <div className="sp-header">
                      <div className="sp-title-row">
                        <UserCircle size={16} />
                        <div>
                          <div className="sp-title">{item.full_name || `Profile #${item.id}`}</div>
                          <div className="sp-meta">{item.location || item.email || 'Profile details available'}</div>
                        </div>
                      </div>
                      {selectedId === item.id ? <span className="sp-badge">Active</span> : null}
                    </div>
                    <div className="sp-body">
                      <p>{item.summary || 'No summary yet.'}</p>
                      <div className="sp-tags">
                        <span>{item.profile_completeness || 0}% complete</span>
                        <span>{(item.skills || []).length || 0} skills</span>
                        <span>{(item.preferred_job_titles || []).length || 0} target roles</span>
                      </div>
                    </div>
                    <div className="sp-actions">
                      {selectedId !== item.id ? (
                        <button className="sel" type="button" onClick={() => handleSelect(item.id)}>
                          <CheckCircle2 size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }} />
                          Set Active
                        </button>
                      ) : null}
                      <button type="button" onClick={() => loadProfileIntoForm(item.id)}>
                        <PencilLine size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }} />
                        Edit
                      </button>
                      <button className="del" type="button" onClick={() => handleDelete(item.id)}>
                        <Trash2 size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'text-bottom' }} />
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {totalProfiles > pageSize ? (
              <div className="pager-ctrl">
                <span className="pager-muted">Page {pageIndex} of {Math.ceil(totalProfiles / pageSize)}</span>
                <div className="pager-btns">
                  <button type="button" disabled={pageIndex === 1} onClick={() => setPageIndex((current) => Math.max(1, current - 1))}>Prev</button>
                  <button type="button" disabled={pageIndex * pageSize >= totalProfiles} onClick={() => setPageIndex((current) => current + 1)}>Next</button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
