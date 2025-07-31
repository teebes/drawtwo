/**
 * Text utility functions
 */

/**
 * Creates initials from a full name by taking the first letter of each word
 * @param name - The full name to create initials from
 * @returns Uppercase initials (e.g., "John Doe" -> "JD")
 */
export const makeInitials = (name: string): string => {
    return name.split(' ').map(word => word[0]).join('').toUpperCase()
}