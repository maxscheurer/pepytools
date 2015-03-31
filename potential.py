import numpy

from reader import read_potential
from constants import BOHRTOAA


class Potential(object):
    """ Representation of a polarizable embedding (PE) potential with
        coordinates, multipole moments, polarizabilities and
        exclusion lists.

        Usually instantiated potential file
        >> pot = Potential.from_file( "myfile.pot" )

        The potential parameters can be accessed through its many
        properties.
    """

    def __init__(self, **kwargs):
        """ Create a potential without content
        """
        self._verbose = kwargs.get('verbose', False)
        self._debug = kwargs.get('debug', False)
        pass

    @classmethod
    def from_file(cls, filename, **kwargs):
        """ Creates a potential from a file
            Arguments:
            filename -- the filename to instantiate the potential from
        """
        a = cls(**kwargs)
        a._filename = filename
        (c, l, m, p, e) = read_potential(filename)
        a.coordinates = c
        a.labels = l
        a.multipoles = m
        a.polarizabilities = p
        a.exclusion_list = e
        hasalpha = numpy.array(a.has_alpha)
        a.field = numpy.zeros( 3*len(hasalpha[numpy.where(hasalpha>-1)] ))
        return a

    @classmethod
    def from_multipoles(cls, coordinates, multipoles, **kwargs):
        """ Creates a potential from a set of coordinates and multipoles
            Arguments:
            coordinates -- the coordinates of the multipoles in Bohr.
            multipoles -- the multipoles to use at the specified coordinates.

            the multipoles can either be a list of charges, such as
            >> q = [[1.0], [-1.0], ...]

            or
            >> q = [1.0, -1.0, ...]

            wheras dipoles must be specified as
            >> d = [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], ...]
        """
        a = cls(**kwargs)

        a.coordinates = numpy.array(coordinates)

        Cl = ['Z' for c in coordinates]
        a.labels = Cl

        m = {0: [[0.0] for c in coordinates],
             1: [[0.0, 0.0, 0.0] for c in coordinates],
             2: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for c in coordinates]}

        # let's see if we have a 'list of stuff' or a dictionary
        if type(multipoles) == type([]) or type(multipoles).__module__ == numpy.__name__:
            for i, value in enumerate(multipoles):

                if type(value) == type([]) or type(value).__module__ == numpy.__name__:

                    # numpy.float64 can enter this block and applying "len" to it is void.
                    if type(value) == numpy.float64:
                        m[0][i] = [float(value)]

                    elif len(value) > 3:
                        raise ValueError("Multipole moments larger than dipoles currently not supported.")

                    elif len(value) == 2:
                        raise ValueError("Multipole moments of length 2 is not understood")

                    elif len(value) == 1:
                        # add the monopole
                        m[0][i] = value
                    else:
                        # add a dipole
                        m[1][i] = value

                elif type(value) == type(0.0):
                    m[0][i] = [value]
                else:
                    raise ValueError("Multipole moments not understood.")

            a.multipoles = m
        elif type(multipoles) == type({}):
            a.multipoles = multipoles
        else:
            raise ValueError("Multipole moments not understood.")


        # now we make fake polarizabilites and exclusion lists
        e = {}
        for i, c in enumerate(coordinates):
            e[i] = numpy.array([-1])

        p = [[0.0 for t in range(6)] for c in coordinates]

        a.exclusion_list = e
        a.polarizabilities = p
        return a

    def getCoordinates(self):
        """ Returns a nsites x 3 array with the coordinates of all
            sites in the potential.
        """
        return self._coordinates

    def setCoordinates(self, coordinates):
        """ Sets the coordinates of system and evaluates the number of sites.

            NB: The coordinates does also include coordinates of non-atomic
                sites such as polarizable sites.

            Arguments:
            coordinates -- the coordinates of the potential
        """
        self._coordinates = coordinates
        self._nsites, n = numpy.shape(coordinates)

    coordinates = property(getCoordinates, setCoordinates,
                           doc='Gets or sets the coordinates of the potential.')

    def getLabels(self):
        return self._labels

    def setLabels(self, labels):
        self._labels = labels

    labels = property(getLabels, setLabels,
                      doc='Gets or stes atomic labels of the potential.')

    def getMultipoles(self):
        return self._multipoles

    def setMultipoles(self, multipoles):
        self._multipoles = multipoles

    multipoles = property(getMultipoles, setMultipoles, doc='Gets or sets the multipoles of the potential.')

    def getPolarizabilities(self):
        """ Returns the polarizabilities of the system.
        """
        return self._polarizabilities

    def setPolarizabilities(self, polarizabilities):
        """ Sets the polarizabilities of the system.

            Arguments:
            polarizabilities -- The polarizability tensors to add.

            NOTE: This will evaluate whether a site is polarizable or not based
                  on the size of the tensor. Currently, it checks if the absolute
                  value of the maximum element is larger than zero.
        """
        if len(polarizabilities) != self.nsites:
            raise ValueError("Number of polarizabilities must match number of sites.")

        self._polarizabilities = polarizabilities
        self._hasalpha = numpy.array([-1 for p in polarizabilities])
        itensor = 0
        for i, tensor in enumerate(polarizabilities):
            if numpy.abs(numpy.max(tensor)) > 0.001:
                self._hasalpha[i] = itensor
                itensor += 1
        self._npols = itensor

    polarizabilities = property(getPolarizabilities, setPolarizabilities, doc='Gets or sets the polarizabilities of the potential.')

    def getExclusionList(self):
        return self._exclusion_list

    def setExclusionList(self, exclusion_list):
        if self._debug:
            print("DEBUG: Setting exclusion list with the following dimension: {} x {}".format(len(exclusion_list.keys()), len(exclusion_list[0])))
        self._exclusion_list = exclusion_list

    exclusion_list = property(getExclusionList, setExclusionList, doc='Gets or sets the exclusion list of the potential.')

    @property
    def nsites(self):
        """ The number of classical sites."""
        return self._nsites

    @property
    def npols(self):
        """ The number of polarizable points."""
        return self._npols

    @property
    def has_alpha(self):
        """ list relating coordinate induces to polarizable points.

            a value of -1 means that the point is not polarizable
        """
        return self._hasalpha

    def get_static_field(self):
        return self.field

    def set_static_field(self, field):
        """ Sets the static field either from a file or from a calculation
        """
        nfield = len(field)
        ff = self.has_alpha
        nalpha = 3*len(ff[numpy.where(ff > -1)])
        nfieldm3 = nfield % 3 == 0
        if len(field) == 3*len(ff[numpy.where(ff > -1)]) and len(field) % 3 == 0:
            self.field = numpy.array(field)
        else:
            print("nfield = {} == 3 x nalpha = {} is {}, nfieldm3 = {}".format(nfield, nalpha, nfield == nalpha, nfieldm3))
            raise ValueError("ERROR: The static field is not appropriate for this potential.")

    def save(self, filename):
        """ Save the potential to a file.

            Arguments:
            filename -- The filename to save to.
        """
        f = open(filename, 'w')
        f.write(str(self))
        f.close()

    def __str__(self):
        """ Converts the potential to a string readable format
        """
        sc = "@COORDINATES\n{0}\nAA\n".format(self.nsites)
        sm = ""
        sp = ""
        se = "\n"
        for label, coord in zip(self.labels, self.coordinates):
            cc = coord * BOHRTOAA
            sc += "{0:2s}{1:14.8f}{2:14.8f}{3:14.8f}\n".format(label, cc[0], cc[1], cc[2])

        if hasattr(self, '_multipoles'):
            sm = "@MULTIPOLES\n"
            for order in self.multipoles.keys():
                sm += "ORDER {0}\n{1}\n".format(order, self.nsites)
                for i, m in enumerate(self.multipoles[order]):
                    sm += "{0:3d}".format(i + 1)
                    for v in m:
                        sm += "{0:14.8f}".format(v)
                    sm += "\n"

        if hasattr(self, '_polarizabilities'):
            sp = "@POLARIZABILITIES\nORDER 1 1\n{0}\n".format(self.nsites)
            for i, poltensor in enumerate(self.polarizabilities):
                sp += "{0:3d}".format(i + 1)
                for v in poltensor:
                    sp += "{0:14.8f}".format(v)
                sp += "\n"

            se = "EXCLISTS\n{0:d} {1:d}\n".format(self.nsites, len(self.exclusion_list[0]) + 1)
            for i in self.exclusion_list.keys():
                se += "{0:>5d}".format(i + 1)
                excl = self.exclusion_list[i] + 1
                for v in excl:
                    se += "{0:5d}".format(v)
                se += "\n"

        return sc + sm + sp + se[:-1]

    def __add__(self, other):
        """ Adds two potential files together.

            >> p3 = p1 + p2

            The strategy is to make an empty potential and copy over
            everything from "self" and "other"
        """
        p = Potential()
        p._verbose = self._verbose or other._verbose
        p._debug = self._debug or other._debug

        c1 = list(self.coordinates)[:]
        c2 = list(other.coordinates)[:]
        c1.extend(c2)
        p.coordinates = numpy.array(c1)

        l1 = self.labels[:]
        l2 = other.labels[:]
        l1.extend(l2)
        p.labels = l1

        # multipoles are stored as a dictionary starting from 0,
        # here we just copy down everything
        m = dict()
        for key in self.multipoles:
            m[key] = list(self.multipoles[key][:])
            m[key].extend(other.multipoles[key][:])
        p.multipoles = m

        pol1 = self.polarizabilities[:]
        pol2 = other.polarizabilities[:]
        pol1.extend(pol2)
        p.polarizabilities = pol1[:]

        # exclusionlists have to be updated so that the id's in the
        # list reflect correct atoms. Offset items in the "other" by
        # the number of polarizable sites. Items with a "-1" should
        # not be updated
        n1 = self.nsites
        n2 = other.nsites
        e1 = self.exclusion_list.copy()
        e2 = other.exclusion_list.copy()

        # find out which one has the more items per key
        ne1 = len(e1[0])
        ne2 = len(e2[0])

        # if e2 has the more items, update elements in e1
        # with the proper length
        if (ne2 > ne1):
            for k in e1.keys():
                items = -1 * numpy.ones(ne2, dtype=int)
                items[:ne1] = e1[k]
                e1[k] = items

        # append e2 to e1
        for k in e2.keys():
            items = -1 * numpy.ones(ne2, dtype=int)
            if (ne1 > ne2):
                items = -1 * numpy.ones(ne1, dtype=int)
            items[:ne2] = e2[k]
            selection = numpy.where(items != -1)
            items[selection] += n1
            e1[k + n1] = items

        p.exclusion_list = e1
        return p

    def __and__(self, other):
        """ Intersection can be computed for two potentials
            by finding appropriate overlapping atoms

            >> p3 = p1 & p2

            One is inclined to remember this 'famous' quote from the
            GAMESS source code:

                This code is hard to read, impossible to debug,
                but it works!

            so to all heathen people, this part of the code has not
            been the most pleasant of adventures.
        """

        satoms = []
        oatoms = []

        slen = self.nsites
        olen = other.nsites
        sc = numpy.array(self.coordinates)
        oc = numpy.array(other.coordinates)

        try:
            from intersect import intersect
            nmax = max(len(sc), len(oc))
            F,n = intersect(nmax, sc, oc)
            satoms = list(F[:n,0])
            oatoms = list(F[:n,1])
        except:

            eps = 1.0e-2
            eps2 = eps*eps

            # first pass is linear in time by comparing atoms directly as we loop over them
            # to avoid expensive pairwise calculations. now the lists might not be equal
            # in length so take the shorter one
            nsites = slen
            if slen > olen:
                nsites = olen

            for ic in range(nsites):
                dr = sc[ic] - oc[ic]
                R2 = dr.dot(dr)
                if R2 < eps2:
                    satoms.append(ic)
                    oatoms.append(ic)

            # single atoms could have been removed, so let's just try again with a spray of offsets
            for ic in range(nsites):
                if ic in satoms:
                    continue

                for offset in [-4, -3, -2, -1, 1, 2, 3, 4]:
                    dr = sc[ic] - oc[ic+offset]
                    R2 = dr.dot(dr)
                    if R2 < eps2:
                        satoms.append(ic)
                        oatoms.append(ic+offset)
                        break

            # next loop is pairwise, looking for all the other ones. do not attempt to use any
            # atoms already in the {s,o}atoms lists.
            for ic in range(nsites):
                if ic in satoms:
                    continue

                for jc in range(nsites):
                    if jc in oatoms:
                        continue

                    dr = sc[ic] - oc[jc]
                    R2 = dr.dot(dr)
                    if R2 < eps2:
                        satoms.append(ic)
                        oatoms.append(jc)
                        break
        # end of try-statement

        # make inverted atom lists to save computation time
        # later on
        smotas = numpy.zeros(max(satoms)+1, dtype=int) -1
        for i, value in enumerate(satoms):
            smotas[value] = i

        smotao = numpy.zeros(max(oatoms)+1, dtype=int) -1
        for i, value in enumerate(oatoms):
            smotao[value] = i

        # get ready to transfer stuff
        p = Potential()
        c = []
        l = []
        pol = []
        m = dict()
        e = dict()

        # so we generate the intersected potential from
        # the "self" using the generated data structures
        # above to find common atoms (and properties).
        #
        # the hard part here is the fields which must be
        # converted from the atom indexing in "other" to
        # one that matches "self" so that they can be
        # correctly dotted later on to give properties.
        sfields_remove = range(slen)
        ofields_remove = range(olen)
        for i, ic in enumerate(satoms):
            c.append( self.coordinates[ic] )
            l.append( self.labels[ic] )
            pol.append( self.polarizabilities[ic] )

            # update the exclusion list to remove any points
            # that are removed
            ex_unfixed = self.exclusion_list[ic]
            ex_fixed = self.fix_exclusion_list( ex_unfixed, smotas )
            e[i] = numpy.array(ex_fixed[:])

            # this takes care of electric field indexing for
            # BOTH the self field and the other field
            sfields_remove[ic] = -1
            ofields_remove[ oatoms[i] ] = -1

        for key in self.multipoles:
            m[key] = []
            for ic in satoms:
                m[key] = list(numpy.zeros(numpy.shape(self._multipoles[key])))

        p.coordinates = numpy.array(c)
        p.labels = l
        p.multipoles = m
        p.polarizabilities = pol[:]
        p.exclusion_list = e

        f1o = self.get_static_field()
        f2o = other.get_static_field()
        nf1o = len(f1o)
        nf2o = len(f2o)
        f1o = f1o.reshape((nf1o/3, 3))
        f2o = f2o.reshape((nf2o/3, 3))

        f1 = []
        for i, ic in enumerate(sfields_remove):
            ii = smotas[i]

            if ii == -1:
                continue

            if ic == -1 and p.has_alpha[ii] != -1:
                f1.append(f1o[ii])

        f2 = []
        for i, ic in enumerate(ofields_remove):
            ii = smotao[i]

            if ii == -1:
                continue

            if ic == -1 and p.has_alpha[ii] != -1:
                f2.append(f2o[ii])

        p.f1 = numpy.ravel(f1)
        p.f2 = numpy.ravel(f2)
        return p

    def fix_exclusion_list( self, exlist, sdi ):
        """ corrects an exclusion list 'exlist' by converting and/or
            removing elements from an old index to a new

            Arguments
            exlist -- the exlcusion list
        """
        new_list = [-1 for i in exlist]
        offset = 0
        for i, value in enumerate(exlist):
            if value == -1:
                break
            if sdi[value] == -1:
                offset -= 1
                continue

            new_list[i+offset] = sdi[value]
        return new_list

    def make_isotropic_polarizabilites(self):
        """ Converts all anisotropic polarizabilities into
            their isotropic counterparts
        """
        pol1 = self.polarizabilities[:]
        pol2 = []
        for pol in pol1:
            value = (pol[0] + pol[3] + pol[5]) / 3.0
            isopol = numpy.zeros(6)
            isopol[0] = value
            isopol[3] = value
            isopol[5] = value
            pol2.append(isopol)
        self.polarizabilities = pol2[:]

    def remove_polarizable_points( self, coordinates, distance ):
        """ The PE library does not remove anything, but it merely sets the polarizabilites
            (and multipoles) to zero.
        """
        d2 = distance*distance

        Cp = list(self.coordinates)
        nCp = range(len(Cp))
        nCp.reverse()

        coordinates_to_remove = []

        for iCp, p in enumerate(Cp):
            for coord in coordinates:
                dr = p - coord
                R2 = dr.dot(dr)
                #print("R = {0:12.6f}, D = {1:12.6f}".format(R2, d2))
                if R2 < d2:
                    coordinates_to_remove.append( iCp )

        # make the list unique
        coordinates_to_remove = [x for x in set(coordinates_to_remove)]
        coordinates_to_remove.sort()
        if self._debug:
            print("Found {} points to remove".format(len(coordinates_to_remove)))

        Ct = list(self.coordinates)
        Cl = list(self.labels)
        M0 = list(self._multipoles[0])
        M1 = list(self._multipoles[1])
        P2 = list(self.polarizabilities)

        for i in coordinates_to_remove:
            M0[i] = [0.0]
            M1[i] = [0.0, 0.0, 0.0]
            P2[i] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        self._multipoles[0] = numpy.array(M0)
        self._multipoles[1] = numpy.array(M1)
        self.polarizabilities = P2[:]

    def make_transition_potential(self):
        """ Sets the static part of the potential equal to zero
        """
        for key in self._multipoles:
            self.multipoles[key] = numpy.zeros(numpy.shape(self._multipoles[key]))

if __name__ == '__main__':
    import sys
    p1 = Potential.from_file(sys.argv[1])

    print p1
