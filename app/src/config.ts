// The repository address comes from repo.json, the one place it is written.
import repo from '../repo.json'

export const REPO = `${repo.owner}/${repo.repo}`
export const REPO_URL = `https://github.com/${REPO}`
export const INSTALL_COMMAND = `claude plugin install ambiance --marketplace ${REPO}`
