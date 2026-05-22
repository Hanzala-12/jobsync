import UniversityMatchList from './UniversityMatchList'

function StudentScholarships({ profileId }) {
  return <UniversityMatchList profileId={profileId} heading="Scholarship Opportunities" initialFilters={{ filter_scholarship_only: true }} />
}

export default StudentScholarships