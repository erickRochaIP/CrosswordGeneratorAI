import sys
import copy, math

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        copyDomains = copy.deepcopy(self.domains)

        for variable, possibleWords in copyDomains.items():
            for word in possibleWords:
                if len(word) != variable.length:
                    self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        sobreposicao = self.crossword.overlaps[x, y]

        copyDomains = copy.deepcopy(self.domains)

        alteracaoFeita = False
        for wordX in copyDomains[x]:
            palavraValida = False
            for wordY in copyDomains[y]:
                if sobreposicao is not None:
                    if wordX[sobreposicao[0]] == wordY[sobreposicao[1]]:
                        palavraValida = True
                        break;
            if len(self.domains[y]) == 1 and wordX in self.domains[y]:
                palavraValida = False
            if palavraValida is False:
                self.domains[x].remove(wordX)
                alteracaoFeita = True

        return alteracaoFeita

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = []
        if arcs is None:
            for (x, y), sobreposicao in self.crossword.overlaps.items():
                if sobreposicao is not None:
                    queue.append((x, y))
        else:
            for arc in arcs:
                queue.append(arc)

        while len(queue) != 0:
            (x, y) = queue.pop()
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                for z in self.crossword.neighbors(x):
                    if z is not y and (z, x) not in queue:
                        queue.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """

        for var in self.crossword.variables:
            if var not in assignment:
                return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        for variableX, wordX in assignment.items():
            if len(wordX) != variableX.length:
                return False

            for variableY, wordY in assignment.items():
                if variableY == variableX:
                    continue
                if wordY is not None and wordX is not None:
                    if wordX == wordY:
                        return False
                sobreposicao = self.crossword.overlaps[variableX, variableY]
                if sobreposicao is not None:
                    if wordX[sobreposicao[0]] != wordY[sobreposicao[1]]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        domain = []
        removedWords = dict()
        for word in self.domains[var]:
            removedWords[word] = 0
            for neighbor in self.crossword.neighbors(var):
                removedWords[word] += self.removedWords(var, neighbor, word, assignment)

        sort_words = sorted(removedWords.items(), key=lambda x: x[1], reverse=False)
        for i in sort_words:
            domain.append(i[0])
        return domain

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        varDomainSize = dict()

        for var in self.crossword.variables:
            if var not in assignment:
                varDomainSize[var] = len(self.domains[var])

        menorValor = math.inf
        for var, size in varDomainSize.items():
            if size < menorValor:
                menorValor = size

        varNeighbors = dict()

        for var, size in varDomainSize.items():
            if size == menorValor:
                varNeighbors[var] = len(self.crossword.neighbors(var))

        sort_nei = sorted(varNeighbors.items(), key=lambda x: x[1], reverse=True)
        for i in sort_nei:
            return i[0]


    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.domains[var]:
            new_assignment = assignment.copy()
            new_assignment[var] = value
            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result

        return None

    def removedWords(self, x, y, wordX, assignment):
        sobreposicao = self.crossword.overlaps[x, y]
        if sobreposicao is None:
            return 0

        palavrasRemovidas = 0
        if assignment[y] is None:
            for wordY in self.domains[y]:
                if wordX[sobreposicao[0]] != wordY[sobreposicao[1]]:
                    palavrasRemovidas += 1

        return palavrasRemovidas


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
